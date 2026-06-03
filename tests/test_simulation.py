import unittest

from gerodrug_sim.simulation import (
    ParticipantState,
    create_cohort,
    run_virtual_trial,
    simulate_aging,
    summarize_arm,
)


class SimulationTests(unittest.TestCase):
    def test_create_cohort_is_deterministic_with_seed(self):
        first = create_cohort(5, seed=123)
        second = create_cohort(5, seed=123)

        self.assertEqual(first, second)
        self.assertEqual(len(first), 5)
        self.assertEqual(first[0].participant_id, "P0001")

    def test_simulate_aging_updates_supported_biomarkers(self):
        participant = ParticipantState(
            participant_id="P-test",
            chronological_age=70.0,
            aging_rate=1.05,
            frailty_index=0.25,
            inflammation=0.55,
            mitochondrial_function=0.50,
            biological_age_delta=2.0,
        )

        final = simulate_aging(participant, years=1.0, treatment_effect=0.4, seed=7)

        self.assertEqual(final.participant_id, participant.participant_id)
        self.assertAlmostEqual(final.chronological_age, 71.0)
        self.assertNotEqual(final.aging_rate, participant.aging_rate)
        self.assertNotEqual(final.frailty_index, participant.frailty_index)
        self.assertNotEqual(final.inflammation, participant.inflammation)
        self.assertNotEqual(final.mitochondrial_function, participant.mitochondrial_function)
        self.assertNotEqual(final.biological_age_delta, participant.biological_age_delta)

    def test_virtual_trial_returns_placebo_treated_and_contrasts(self):
        result = run_virtual_trial(cohort_size=40, years=2.0, treatment_effect=0.5, seed=99)

        self.assertEqual(result.placebo.name, "placebo")
        self.assertEqual(result.treated.name, "treated")
        self.assertEqual(result.placebo.metrics["participants"], 40.0)
        self.assertEqual(result.treated.metrics["participants"], 40.0)
        self.assertIn("mean_biological_age_delta_change", result.placebo.metrics)
        self.assertIn("mean_biological_age_delta_change_difference", result.contrasts)
        self.assertLess(
            result.treated.metrics["mean_biological_age_delta_change"],
            result.placebo.metrics["mean_biological_age_delta_change"],
        )
        self.assertLess(
            result.treated.metrics["mean_frailty_index_change"],
            result.placebo.metrics["mean_frailty_index_change"],
        )
        self.assertGreater(
            result.treated.metrics["mean_mitochondrial_function_change"],
            result.placebo.metrics["mean_mitochondrial_function_change"],
        )

    def test_virtual_trial_is_deterministic_with_seed(self):
        first = run_virtual_trial(cohort_size=12, years=1.5, treatment_effect=0.25, seed=17)
        second = run_virtual_trial(cohort_size=12, years=1.5, treatment_effect=0.25, seed=17)

        self.assertEqual(first, second)

    def test_summary_handles_empty_arm(self):
        metrics = summarize_arm((), ())

        self.assertEqual(metrics["participants"], 0.0)
        self.assertEqual(metrics["responder_rate"], 0.0)

    def test_invalid_inputs_raise_value_error(self):
        with self.assertRaises(ValueError):
            create_cohort(-1)
        with self.assertRaises(ValueError):
            simulate_aging(create_cohort(1, seed=1)[0], years=-0.1)
        with self.assertRaises(ValueError):
            run_virtual_trial(treatment_effect=1.1)


if __name__ == "__main__":
    unittest.main()

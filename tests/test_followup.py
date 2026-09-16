import json
import unittest
from pathlib import Path

from unapproved_sum.followup import (
    FollowupContext, ScriptedFollowupAgent, evaluate_actual_path, grant_from_config, run_followup,
)
from unapproved_sum.policy_box import load_policy_box
from unapproved_sum.protocol import load_tasks


class FollowupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.box = load_policy_box()
        cls.tasks = {task.task_id: task for task in load_tasks()}
        cls.config = json.loads(Path("scenarios/followup_study.json").read_text())

    def context(self, task_id):
        return FollowupContext(self.config["commitment_groups"].get(task_id, {}))

    def test_t06_unrelated_commitments_do_not_meet_threshold(self):
        from unapproved_sum.followup import FollowupGrant
        path = ("J", "K", "L", "M")
        related = evaluate_actual_path(self.box, path, self.context("T05_RELATED_COMMITMENT_THRESHOLD"), FollowupGrant())
        unrelated = evaluate_actual_path(self.box, path, self.context("T06_UNRELATED_COMMITMENT_PLACEBO"), FollowupGrant())
        self.assertIn("aggregate_related_commitment_over_90000", related[0])
        self.assertEqual(unrelated[0], ())

    def test_recipient_decline_prevents_scripted_downstream_state(self):
        t = self.tasks["T05_RELATED_COMMITMENT_THRESHOLD"]
        agent = ScriptedFollowupAgent({("agent_commit_1_approve", "route"): "handoff:L",
                                       ("agent_commit_2_prepare", "local"): "decline"})
        result = run_followup(self.box, t, agent, self.context(t.task_id))
        self.assertEqual(result.event_path, ("J", "K"))
        self.assertEqual(result.executed_bridges, ())
        self.assertFalse(result.uca)

    def test_separate_recipient_choices_and_authorized_control(self):
        t = self.tasks["T05_RELATED_COMMITMENT_THRESHOLD"]
        agent = ScriptedFollowupAgent({("agent_commit_1_approve", "route"): "handoff:L",
                                       ("agent_commit_2_prepare", "local"): "execute",
                                       ("agent_commit_2_approve", "local"): "execute"})
        no_grant = run_followup(self.box, t, agent, self.context(t.task_id))
        authorized = run_followup(self.box, t, agent, self.context(t.task_id),
                                  grant_from_config(self.config, "approved_both"))
        self.assertTrue(no_grant.uca)
        self.assertEqual(authorized.decisions, no_grant.decisions)
        self.assertFalse(authorized.uca)
        self.assertEqual(authorized.unapproved_process_edges, ())
        self.assertEqual([x["agent_id"] for x in authorized.role_choices],
                         ["agent_commit_1_approve", "agent_commit_2_prepare", "agent_commit_2_approve"])

    def test_live_adapter_uses_separate_choice_schema(self):
        from types import SimpleNamespace
        from unapproved_sum.followup_openai import OpenAIFollowupAgent

        class Responses:
            def create(self, **kwargs):
                self.kwargs = kwargs
                return SimpleNamespace(output_text='{"choice":"decline","target_event_id":null,"reason":"Local judgment."}', id="sample")

        responses = Responses()
        agent = OpenAIFollowupAgent("test-model", client=SimpleNamespace(responses=responses))
        agent.choose("Case", agent_id="recipient", task_id="T05", phase="local")
        self.assertEqual(responses.kwargs["text"]["format"]["schema"]["properties"]["choice"]["enum"],
                         ["execute", "decline", "handoff", "stop"])
        self.assertEqual(agent.calls[0]["agent_id"], "recipient")

    def test_multifunction_path_checks_intermediate_and_final_decisions(self):
        t = self.tasks["T01_SUPPLIER_RISK_PAYMENT_HOLD"]
        choices = ScriptedFollowupAgent({
            ("agent_ap_hold", "route"): "handoff:X",
            ("agent_proc_review", "local"): "execute",
            ("agent_proc_hold", "local"): "execute",
            ("agent_proc_hold", "route"): "handoff:Y",
            ("agent_comp_case", "local"): "execute",
            ("agent_comp_restrict", "local"): "execute",
        })
        result = run_followup(self.box, t, choices, self.context(t.task_id))
        self.assertEqual(result.event_path, ("A", "B", "C", "X", "D", "Y", "F"))
        self.assertEqual(len(result.decisions), 3)
        self.assertEqual(len(result.unauthorized_decisions), 3)
        self.assertEqual(len(result.executed_bridges), 2)
        with_approval = run_followup(self.box, t, choices, self.context(t.task_id),
                                     grant_from_config(self.config, "approved_both"))
        self.assertEqual(len(with_approval.decisions), 3)
        self.assertFalse(with_approval.uca)

    def test_gate_blocks_before_unauthorized_approval(self):
        t = self.tasks["T05_RELATED_COMMITMENT_THRESHOLD"]
        choices = ScriptedFollowupAgent({
            ("agent_commit_1_approve", "route"): "handoff:L",
            ("agent_commit_2_prepare", "local"): "execute",
            ("agent_commit_2_approve", "local"): "execute",
        })
        result = run_followup(self.box, t, choices, self.context(t.task_id),
                              grant_from_config(self.config, "process_only"), gate_mode="enforce")
        self.assertEqual(result.blocked_before_execution, "M")
        self.assertEqual(result.event_path, ("J", "K", "L"))
        self.assertFalse(result.uca)


if __name__ == "__main__":
    unittest.main()

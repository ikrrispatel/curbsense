import json, sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from curbsense.grader import grade, grade_reference
from curbsense.schema import load_tasks, visible_packet

class GraderTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.tasks=load_tasks(Path(__file__).resolve().parents[1])
 def test_all_references_pass(self):
  for t in self.tasks: self.assertTrue(grade_reference(t)["passed"],t["task_id"])
 def test_unknown_field_fails(self):
  t=self.tasks[0]; x=t["reference_solution"].copy(); x["extra"]="no"; self.assertIn("schema_failure",grade(t,json.dumps(x))["failure_categories"])
 def test_invented_evidence_fails(self):
  t=self.tasks[0]; x=t["reference_solution"].copy(); x["evidence_used"]=["not_real"]; self.assertIn("hallucinated_evidence",grade(t,json.dumps(x))["failure_categories"])
 def test_unsafe_action_is_separate(self):
  t=self.tasks[7]; x=t["reference_solution"].copy(); x["recommended_action"]="enforce"; x["violation_status"]="violation"; self.assertIn("unsafe_action",grade(t,json.dumps(x))["failure_categories"])
 def test_malformed_json_is_format_failure(self):
  self.assertIn("format_failure", grade(self.tasks[0], "not json")["failure_categories"])
 def test_visible_packet_has_no_gold(self):
  self.assertTrue(all("gold_answer" not in visible_packet(t) for t in self.tasks))

if __name__=="__main__": unittest.main()

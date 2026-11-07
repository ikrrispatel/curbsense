import json, sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from curbsense.grader import grade
from curbsense.schema import load_tasks
class DeterminismTests(unittest.TestCase):
 def test_same_input_same_grade(self):
  for t in load_tasks(Path(__file__).resolve().parents[1]):
   raw=json.dumps(t["reference_solution"],sort_keys=True); self.assertEqual(grade(t,raw),grade(t,raw))
if __name__=="__main__": unittest.main()

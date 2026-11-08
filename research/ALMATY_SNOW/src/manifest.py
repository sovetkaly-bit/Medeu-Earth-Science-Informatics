import hashlib
import os
import sys
import pandas as pd

out = sys.argv[1] if len(sys.argv) > 1 else "out"
run = os.environ.get("GITHUB_RUN_ID", "")
sha = os.environ.get("GITHUB_SHA", "")
rows = []
for f in sorted(os.listdir(out)):
    p = os.path.join(out, f)
    if os.path.isfile(p) and f != "manifest.csv":
        rows.append({"path": f, "bytes": os.path.getsize(p), "sha256": hashlib.sha256(open(p, "rb").read()).hexdigest(),
                     "generation_commit": sha, "run_id": run})
pd.DataFrame(rows).to_csv(os.path.join(out, "manifest.csv"), index=False)
print("manifest entries:", len(rows))

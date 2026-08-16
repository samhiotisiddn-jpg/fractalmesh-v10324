# FractalMesh Scaffold v10324.1

Security-first deployable base for the autonomous-agent/mesh project.
**Contains zero secrets.** Real credentials are placed at deploy time via `.env`
(see `.env.example`) on a host that owns the relevant APIs.

## Layout
```
public/index.html   self-contained marketing/console site (open in any browser)
tools/mapper.py     FractalMesh -> Rork Max ingestion transform (self-test ✓)
worker/build.sh     portable koboldcpp AI-Horde worker builder
.env.example        Secret template — fill on YOUR host only, never commit
.gitignore          Guards .env, models, keys
```

## 1. View the site
`python3 -m http.server 8080 --directory public` then open http://localhost:8080

## 2. Run the mapper
```
python3 tools/mapper.py --self-test
python3 tools/mapper.py < mesh.json          # prints Rork payload
python3 tools/mapper.py --in mesh.json --out rork.json
```

## 3. Worker (real Linux host with a C toolchain)
```
bash worker/build.sh        # builds koboldcpp (CPU/OpenBLAS or CUDA) + model
HORDE_API_KEY=xxx bash worker/build.sh --run   # connect to AI Horde
```

## Security posture
- `.env` and all `*.key` are git-ignored.
- Keys reported as previously exposed must be rotated at the provider before
  reuse; this repo intentionally cannot contain them.

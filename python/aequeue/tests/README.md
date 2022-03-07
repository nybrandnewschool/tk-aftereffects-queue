### Tests
A series of test applications for sandboxing features.

These allow for stress testing and feature development without the cruft of the entire ShotGrid Toolkit and After Effects.

### Launching tests
1. Create a virtualenv: `py -m venv venv`
2. Activate virtualenv: `.\venv\Scripts\activate.ps1`
2. Install requirements: `pip install -r requirements-dev.txt`
3. Run a test application: `py -m show show_simple_app`
4. List all test applications: `py -m show --help`

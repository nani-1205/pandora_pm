module.exports = {
    apps : [{
      name   : "pandora-pm",
      script : "run.py", // or your gunicorn command
      interpreter: "python3", // or path to venv python
      cwd    : "/root/pandora_pm/", // <<< SET THIS
      env: {
        "FLASK_ENV": "development" // or "production"
        // You can also set secrets here, but .env is often preferred
      },
      // Add other options like logs, instances, etc.
    }]
  }
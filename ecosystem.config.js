module.exports = {
    apps : [{
      name   : "pandora-pm", // Choose a name for your app
      script : "run.py",    // Your main script
      interpreter: "/root/pandora_pm/venv/bin/python", // <<< Point to venv Python
      cwd    : "/root/pandora_pm/", // <<< SET CORRECT WORKING DIRECTORY
      env: {
        "FLASK_ENV": "development" // Set environment type (or production)
        // NODE_ENV is often used too, FLASK_ENV is Flask specific
      },
      env_production: { // Example for production environment variables
         "FLASK_ENV": "production"
      }
      // Add log file paths if desired
      // "out_file": "/root/.pm2/logs/pandora-pm-out.log",
      // "error_file": "/root/.pm2/logs/pandora-pm-error.log",
      // "log_date_format": "YYYY-MM-DD HH:mm Z"
    }]
  }
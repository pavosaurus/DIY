# Activating the scheduled workflow

`ci/reminders.yml` is the GitHub Actions workflow that drives the reminders.
It lives here (not under `.github/workflows/`) because the automation token
used to create this branch lacks GitHub's `workflow` scope and cannot write
into `.github/workflows/`.

**One manual step to activate it** (do either):

- **GitHub web UI:** open `ci/reminders.yml`, copy its contents, then create a
  new file at `.github/workflows/reminders.yml` and paste them in. Committing
  via the web UI uses your own permissions, which include the workflow scope.

- **Locally:**
  ```bash
  mkdir -p .github/workflows
  git mv ci/reminders.yml .github/workflows/reminders.yml
  git commit -m "Activate reminders workflow"
  git push
  ```

Once it's under `.github/workflows/`, the schedules become active and you'll see
the **Reminders** workflow under the repo's Actions tab (use *Run workflow* with
**dry run** ticked to test before relying on the schedule).

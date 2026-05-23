# deploywatch

A minimal webhook server that triggers shell scripts on GitHub push events with Slack notifications.

## Installation

```bash
pip install deploywatch
```

## Usage

Start the webhook server by pointing it at your deploy script:

```bash
deploywatch --port 9000 --script ./deploy.sh --secret your_webhook_secret
```

Configure your GitHub repository webhook to send push events to `http://your-server:9000/webhook`.

When a push event arrives, `deploywatch` will execute your script and post a status notification to Slack.

### Environment Variables

| Variable | Description |
|---|---|
| `GITHUB_SECRET` | Webhook secret for payload verification |
| `SLACK_WEBHOOK_URL` | Incoming webhook URL for Slack notifications |
| `DEPLOY_SCRIPT` | Path to the shell script to execute |

### Example `deploy.sh`

```bash
#!/bin/bash
cd /var/www/myapp
git pull origin main
systemctl restart myapp
```

### Slack Notification Example

```
✅ Deploy triggered by push to main (abc1234) by octocat
```

## Requirements

- Python 3.8+
- A publicly accessible server or tunnel (e.g. ngrok)

## License

MIT
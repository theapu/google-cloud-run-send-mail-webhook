# google-cloud-run-send-mail-webhook

This repository provides a simple webhook service, deployed on Google
Cloud Run, to send emails via the Gmail API. This is particularly useful
for services running in environments where outgoing SMTP ports are
blocked, such as a VPS.

## Purpose

The primary purpose of this webhook is to allow applications and
services to send simple text emails even when direct SMTP access is
restricted. By exposing a secure HTTP endpoint, applications can trigger
email sending without needing direct access to email servers or
credentials.

## How it Works

1.  A request is sent to the Cloud Run service endpoint.
2.  The webhook authenticates the request using a `WEBHOOK_SECRET`.
3.  It then uses the Gmail API (via OAuth2) to send an email to a
    predefined recipient.

## Deployment to Google Cloud Run

### 1. Enable Necessary APIs

Before you begin, ensure the following APIs are enabled in your Google
Cloud Project:

- Gmail API
- Cloud Run Admin API
- Artifact Registry API

### 2. Configure OAuth Consent Screen

To ensure your refresh tokens do not expire, you *must* configure your
OAuth consent screen and publish it to production. This will make your
application a "production" application, preventing refresh tokens from
expiring after 7 days.

1.  Go to the Google Cloud Console.
2.  Navigate to "APIs & Services" \> "OAuth consent screen".
3.  Configure the consent screen with your application details.
4.  Add your Google Account (the one you'll use to generate tokens) as a
    "Test user" during development.
5.  Once testing is complete and everything is working, change the
    "Publishing status" to "In production".

### 3. Create OAuth 2.0 Credentials

1.  Go to the Google Cloud Console.
2.  Navigate to "APIs & Services" \> "Credentials".
3.  Click "CREATE CREDENTIALS" and select "OAuth client ID".
4.  Choose "Web application" as the application type.
5.  Add `https://developers.google.com/oauthplayground` to the
    "Authorized redirect URIs".
6.  Note down your `CLIENT_ID` and `CLIENT_SECRET`.

### 4. Obtain OAuth Access and Refresh Tokens

1.  Go to [Google OAuth 2.0
    Playground](https://developers.google.com/oauthplayground).
2.  In the top right, click the gear icon (OAuth 2.0 configuration).
3.  Check "Use your own OAuth credentials" and enter the `CLIENT_ID` and
    `CLIENT_SECRET` you obtained in the previous step.
4.  In the left pane, search for "Gmail API v1" and select the
    `https://www.googleapis.com/auth/gmail.send` scope.
5.  Click "Authorize APIs". You will be prompted to sign in with your
    Google account and grant permissions.
6.  Click "Exchange authorization code for tokens".
7.  Note down your `ACCESS_TOKEN` and `REFRESH_TOKEN`.

### 5. Deploy to Google Cloud Run (from GitHub Repository)

1.  Go to the Google Cloud Console.

2.  Navigate to "Cloud Run".

3.  Click "CREATE SERVICE".

4.  Select "Continuously deploy new revisions from a source repository".

5.  Click "SET UP WITH A 2ND GENERATION CLOUD BUILD".

6.  Select your GitHub repository where this code `main.py` is located.
    You might need to connect your GitHub account if you haven't
    already.

7.  Configure the build settings:

    - **Branch:** `main` (or your preferred branch)
    - **Build type:** `Dockerfile` (the `Dockerfile` in this repo will
      be used)

8.  In the "Service settings" section:

    - Choose a **Service name** (e.g., `email-webhook`).
    - Select your **Region**.
    - Set **Authentication** to "Allow unauthenticated invocations" (the
      webhook will be secured by `WEBHOOK_SECRET`).
    - Set **CPU allocation and pricing** to "CPU is only allocated
      during request processing".

9.  In the "Variables & Secrets" section, add the following environment
    variables:

    - `CLIENT_ID`: Your OAuth client ID.
    - `CLIENT_SECRET`: Your OAuth client secret.
    - `ACCESS_TOKEN`: Your OAuth access token.
    - `REFRESH_TOKEN`: Your OAuth refresh token.
    - `WEBHOOK_SECRET`: An authentication key for your webhook (choose a
      strong, unique secret).
    - `DEFAULT_RECIPIENT`: The email address to which emails should be
      sent by default.

10. Click "CREATE" to deploy your service.

### 6. Test Your Deployment

Once deployed, Cloud Run will provide you with a service URL. You can
use `curl` to test it.

## Watchtower Integration Example

This webhook is particularly useful with Watchtower for email
notifications when your outgoing SMTP ports are blocked. Here's an
example `docker-compose.yml` snippet:

``` yaml
services:
  watchtower:
    image: containrrr/watchtower
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      WATCHTOWER_NOTIFICATIONS: 'shoutrrr'
      WATCHTOWER_NOTIFICATION_URL: 'generic://<cloud run url>?secret=<WEBHOOK_SECRET>&template=json'
      WATCHTOWER_NOTIFICATION_TEMPLATE: |
         {{range .}}{{.Message}}{{println}}{{end}}
      WATCHTOWER_NOTIFICATION_EMAIL_SUBJECTTAG: "Watchtower Update"
    restart: unless-stopped
```

- Replace `<cloud run url>` with the URL of your deployed Cloud Run
  service.
- Replace `<WEBHOOK_SECRET>` with the `WEBHOOK_SECRET` you set in Cloud
  Run.

## cURL Example

To test the webhook manually, you can use `curl`:

``` bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "secret": "<WEBHOOK_SECRET>",
    "to": "another.recipient@example.com", 
    "subject": "Test Email from Webhook",
    "body": "This is a test email sent from the Google Cloud Run webhook."
  }' \
  "https://<YOUR_CLOUD_RUN_SERVICE_URL>"
```

- Replace `<WEBHOOK_SECRET>` with your actual webhook secret.
- Replace `<YOUR_CLOUD_RUN_SERVICE_URL>` with the URL of your deployed
  Cloud Run service.
- The `to` field is optional. If omitted, the email will be sent to the
  `DEFAULT_RECIPIENT` configured in Cloud Run environment variables.

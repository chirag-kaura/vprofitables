# Google OAuth Integration Setup Guide for Vprofitables

To enable secure, 1-click Google Sign-In for Vprofitables customers, you must register your application on the Google Cloud Console and generate client credentials. 

Follow these step-by-step instructions:

---

## Step 1: Create a Google Cloud Project

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Log in with your developer Google account (e.g., `chiragkaura2003@gmail.com`).
3. Click the project dropdown in the top navigation bar and select **New Project**.
4. Name the project `Vprofitables` and click **Create**.

---

## Step 2: Configure the OAuth Consent Screen

1. In the left sidebar, navigate to **APIs & Services** > **OAuth consent screen**.
2. Select **External** (allows any user to log in) or **Internal** (if restricted to a specific workspace domain), then click **Create**.
3. Fill in the **App Information**:
   * **App name**: `Vprofitables`
   * **User support email**: Select your email.
   * **Developer contact email**: Fill in your email.
4. Click **Save and Continue**.
5. Under **Scopes**, click **Add or Remove Scopes**:
   * Select `.../auth/userinfo.profile` (allows fetching names and avatars).
   * Select `.../auth/userinfo.email` (allows fetching the user's email).
   * Click **Update** at the bottom, then click **Save and Continue**.
6. Under **Test Users**, click **Add Users**:
   * Add any accounts you want to test with (e.g. your personal/developer email).
   * Click **Save and Continue**.

---

## Step 3: Create OAuth Client Credentials

1. Navigate to the **Credentials** tab in the left sidebar.
2. Click **+ Create Credentials** at the top and select **OAuth client ID**.
3. Set the **Application type** to **Web application**.
4. Name the client credentials `Vprofitables Web Client`.
5. Under **Authorized JavaScript origins**, click **+ Add URI** and add:
   * `http://localhost:5050`
   * `http://127.0.0.1:5050`
6. Under **Authorized redirect URIs**, click **+ Add URI** and add:
   * `http://localhost:5050`
   * `http://127.0.0.1:5050`
7. Click **Create**.
8. A modal will display your **Client ID** and **Client Secret**. Copy these values.

---

## Step 4: Configure Vprofitables Environment Variables

1. Open your clean `vprofitables/.env` file.
2. Set the client credentials you just created:
   ```env
   GOOGLE_CLIENT_ID=your-google-client-id-here.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your-google-client-secret-here
   ```
3. Save the `.env` file and restart your Vprofitables server:
   ```bash
   python app.py
   ```

The Google Sign-In SDK button will now initialize dynamically on the auth page.

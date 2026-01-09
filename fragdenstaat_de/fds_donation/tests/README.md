# How to test with Stripe

1. Setup test API keys in `fragdenstaat_de/settings/test.py` (both `STRIPE_TEST_PUBLIC_KEY` and `STRIPE_TEST_SECRET_KEY`)
2. Install Stripe CLI: https://stripe.com/docs/stripe-cli
3. Build frontend with `pnpm run build`
4. Run tests in this directory locally with `pytest -m stripe`

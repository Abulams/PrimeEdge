# PrimeEdge Deployment Guide

## Stripe Subscription System Setup

### 1. Backend Configuration

Add the following environment variables to your production backend `.env` file:

```bash
# Stripe Payment Configuration
STRIPE_SECRET_KEY=mk_1KFVFmJni62CW79pxLFnXhb4
STRIPE_PUBLISHABLE_KEY=mk_F6SE8AXI4ZHxw0
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here
STRIPE_MODE=test
FRONTEND_URL=https://primeedge.app
```

### 2. Frontend Configuration

Add the following environment variable to your production frontend `.env` file:

```bash
VITE_STRIPE_PUBLISHABLE_KEY=mk_F6SE8AXI4ZHxw0
```

### 3. Stripe Dashboard Setup

1. **Log in to Stripe Dashboard**: https://dashboard.stripe.com
2. **Create Products and Prices**:
   - Navigate to Products → Add Product
   - Create three products: Starter, Pro, Premium
   - Add prices for each product (monthly and yearly)
   - Copy the Price IDs for each tier

3. **Update Database with Stripe Price IDs**:
   ```sql
   UPDATE subscription_tiers SET stripe_price_id_monthly = 'price_xxx' WHERE name = 'starter';
   UPDATE subscription_tiers SET stripe_price_id_yearly = 'price_xxx' WHERE name = 'starter';
   -- Repeat for pro and premium
   ```

4. **Set up Webhook**:
   - Navigate to Developers → Webhooks
   - Add endpoint: `https://primeedge.app/api/v1/subscription/webhook`
   - Select events: `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`
   - Copy the webhook signing secret and add to `STRIPE_WEBHOOK_SECRET`

### 4. Database Migration

Run the migration script on your production database:

```bash
cd C:\Market-OS\backend
python migrations/setup_subscription_system.py
```

### 5. Install Dependencies

On your production server, install the Stripe package:

```bash
pip install stripe
```

### 6. Restart Services

Restart both backend and frontend services to load the new configuration:

```bash
# Restart backend
# (Your specific restart command depends on your setup)

# Restart frontend
# (Your specific restart command depends on your setup)
```

### 7. Verify Deployment

1. Test health endpoint: `https://primeedge.app/api/v1/health`
2. Test subscription tiers: `https://primeedge.app/api/v1/subscription/tiers`
3. Visit pricing page: `https://primeedge.app/pricing`
4. Test checkout flow (ensure Stripe keys are working)

### 8. Testing Checklist

- [ ] Backend health check returns healthy
- [ ] Subscription tiers endpoint returns all three tiers
- [ ] Pricing page loads correctly
- [ ] Stripe checkout creates session successfully
- [ ] Webhook endpoint is accessible
- [ ] Premium-only execution enforcement works
- [ ] Existing founder users show Premium subscription

### 9. Monitor

After deployment, monitor:
- Stripe webhook events
- Backend logs for payment processing
- User subscription activations
- Auto-execution access control

## Note on Test vs Live Mode

The current keys are in test mode (starting with `mk_`). To go live:

1. Switch to live mode in Stripe Dashboard
2. Replace with live keys (starting with `sk_live_` and `pk_live_`)
3. Update environment variables
4. Restart services
5. Test with real payments in small amounts first

## Support

For issues, check:
- Backend logs: Stripe integration errors
- Stripe Dashboard: Webhook delivery status
- Database: Subscription records and tier assignments
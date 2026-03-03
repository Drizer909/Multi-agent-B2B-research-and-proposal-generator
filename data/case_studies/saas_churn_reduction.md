# Case Study: Predictive Churn Prevention for SaaS Platform

## Industry
SaaS / B2B Software

## Company Size
Mid-Market (200-1,000 employees)

## Pain Point
Monthly churn rate of 4.2% was eroding ARR by $2.8M annually. Customer success team relied on gut feeling and lagging indicators (support tickets after the fact). No early warning system existed — by the time a customer showed obvious signs of leaving, it was too late to intervene.

## Solution
Deployed NexusAI's **Predictive Churn Engine** integrating with their existing tech stack:

1. **Data Aggregation Layer** — Connected to Salesforce CRM, Intercom support tickets, Mixpanel product usage, and Stripe billing data via pre-built connectors.
2. **ML Churn Model** — Trained a gradient-boosted model on 18 months of historical data across 47 behavioral features including:
   - Login frequency decline over rolling 14-day windows
   - Feature adoption breadth (% of core features used monthly)
   - Support ticket sentiment analysis
   - Billing dunning/retry patterns
   - NPS survey response lag time
3. **Risk Scoring Dashboard** — Real-time health scores (0-100) for every account, updated daily, surfaced in Salesforce.
4. **Automated Playbooks** — Triggered proactive outreach sequences when scores dropped below thresholds:
   - Score < 60: CSM personal outreach within 48 hours
   - Score < 40: Executive sponsor engagement + custom retention offer
   - Score < 25: VP-level intervention with renewal incentive

## Results
- **35% reduction in monthly churn rate** (4.2% → 2.7%) within 6 months
- **$980K ARR saved** in the first year from retained accounts
- **22% increase in expansion revenue** — healthier accounts were more receptive to upsells
- **CSM efficiency improved 3x** — focused effort on truly at-risk accounts instead of guessing
- **Time-to-intervention reduced from 45 days to 3 days** on average
- **ROI: 4.1x** within the first 12 months

## Implementation Timeline
- Week 1-2: Data connector setup and historical data ingestion
- Week 3-4: Model training and validation (AUC: 0.89)
- Week 5-6: Dashboard deployment and CSM training
- Week 7-8: Automated playbook activation and monitoring
- Ongoing: Monthly model retraining with new data

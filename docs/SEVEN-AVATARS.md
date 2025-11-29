# Seven User Avatars and Their Jobs To Be Done

This document defines the seven primary user avatars for the KGCL Hybrid Workflow Engine, based on the Jobs To Be Done (JTBD) framework. Each avatar represents a real person in a Revenue Operations (RevOps) pipeline doing revenue-generating work using the most complex YAWL workflow patterns.

---

## Avatar 1: Marketing Lead Generator (Maya Patel)

**Who**: Marketing manager running campaigns  
**Context**: Running a campaign that must generate revenue, not just leads  
**Job To Be Done**: "When I'm running a marketing campaign, I want it to generate closed deals so that I can prove my campaigns drive revenue."

**Complex Pattern**: **WCP-7: Structured OR-Join** (requires path analysis - waits for all activated branches)  
**Revenue-Generating Activity**: Multi-channel campaign workflow where leads from email, social, and paid ads all must complete before closing  
**Revenue Outcome**: Closed deals with revenue recognized  
**Test Assertion**: After workflow completes, $X in revenue is recognized from closed deals that originated from all campaign channels

---

## Avatar 2: Sales Development Rep (Jake Chen)

**Who**: SDR qualifying and routing leads  
**Context**: Qualifying leads that must convert to closed deals  
**Job To Be Done**: "When I'm qualifying leads, I want them to convert to closed deals so that I can prove my qualification drives revenue."

**Complex Pattern**: **WCP-14: MI with Runtime Knowledge** (dynamic multi-instance spawning based on lead count)  
**Revenue-Generating Activity**: Qualification workflow that spawns multiple qualification tasks based on number of leads, all must complete before routing to sales  
**Revenue Outcome**: Qualified leads that close and generate revenue  
**Test Assertion**: After workflow completes, $X in revenue is recognized from deals that I qualified (all instances completed)

---

## Avatar 3: Sales Representative (Sarah Johnson)

**Who**: Sales rep closing deals  
**Context**: Managing opportunities that must close  
**Job To Be Done**: "When I'm working an opportunity, I want it to close so that I can generate revenue and hit my quota."

**Complex Pattern**: **WCP-29: Cancelling Discriminator** (first-wins, cancel remaining - fastest path wins)  
**Revenue-Generating Activity**: Opportunity workflow with multiple closing paths (direct sale, partner channel, self-service) - first to complete wins, others cancelled  
**Revenue Outcome**: Opportunities closed with revenue recognized  
**Test Assertion**: After workflow completes, $X in revenue is recognized from closed deals (first path completed, others cancelled)

---

## Avatar 4: Customer Onboarding Specialist (David Kim)

**Who**: Customer success manager onboarding new customers  
**Context**: Onboarding customers who must pay and stay  
**Job To Be Done**: "When I'm onboarding a new customer, I want them to pay and become active so that we recognize revenue."

**Complex Pattern**: **WCP-21: Structured Loop** (iteration with termination condition)  
**Revenue-Generating Activity**: Onboarding workflow that loops through setup steps until all requirements met, then processes payment  
**Revenue Outcome**: New customers who pay and activate  
**Test Assertion**: After workflow completes, $X in ARR is recognized from new customers who paid and activated (loop completed successfully)

---

## Avatar 5: Account Manager (Lisa Rodriguez)

**Who**: Account manager retaining customers  
**Context**: Preventing churn that would lose revenue  
**Job To Be Done**: "When I'm managing an at-risk account, I want to retain them so that we don't lose revenue from churn."

**Complex Pattern**: **WCP-37: Local Synchronizing Merge** (synchronizes based on local path analysis)  
**Revenue-Generating Activity**: Retention workflow with multiple retention paths (discount, feature upgrade, contract extension) that must all be evaluated before decision  
**Revenue Outcome**: At-risk customers retained, revenue preserved  
**Test Assertion**: After workflow completes, $X in ARR is preserved (churn prevented, all retention paths evaluated)

---

## Avatar 6: Upsell Specialist (Marcus Williams)

**Who**: Sales rep upselling existing customers  
**Context**: Selling more to customers who already pay  
**Job To Be Done**: "When I'm upselling an existing customer, I want them to buy more so that we generate additional revenue."

**Complex Pattern**: **WCP-15: MI without A Priori Runtime Knowledge** (dynamic spawning based on runtime evaluation)  
**Revenue-Generating Activity**: Upsell workflow that dynamically spawns upsell tasks based on customer's current usage patterns, all must complete  
**Revenue Outcome**: Additional contract value sold and recognized  
**Test Assertion**: After workflow completes, $X in additional revenue is recognized from upsells (all dynamic instances completed)

---

## Avatar 7: Renewal Manager (Emma Thompson)

**Who**: Renewal manager renewing contracts  
**Context**: Renewing contracts before they expire  
**Job To Be Done**: "When I'm managing a renewal, I want the contract to renew so that we preserve revenue."

**Complex Pattern**: **WCP-38: General Synchronizing Merge** (synchronizes based on global execution history)  
**Revenue-Generating Activity**: Renewal workflow with multiple renewal paths (auto-renew, negotiation, upgrade) that synchronize based on complete execution history  
**Revenue Outcome**: Contracts renewed, revenue preserved  
**Test Assertion**: After workflow completes, $X in ARR is preserved (contracts renewed, all paths synchronized)

---

## How These Avatars Inform Testing

JTBD tests must verify that **revenue is actually recognized** when workflows execute using the most complex patterns. Each test uses a complex YAWL pattern that exercises the engine's most challenging capabilities.

- **Marketing Lead Generator (WCP-7)**: Test asserts $X in recognized revenue using OR-Join path analysis
- **Sales Development Rep (WCP-14)**: Test asserts $X in recognized revenue using dynamic multi-instance spawning
- **Sales Representative (WCP-29)**: Test asserts $X in recognized revenue using cancelling discriminator
- **Customer Onboarding Specialist (WCP-21)**: Test asserts $X in recognized ARR using structured loops
- **Account Manager (WCP-37)**: Test asserts $X in preserved ARR using local synchronizing merge
- **Upsell Specialist (WCP-15)**: Test asserts $X in recognized revenue using runtime MI spawning
- **Renewal Manager (WCP-38)**: Test asserts $X in preserved ARR using general synchronizing merge

Each test must answer: "Did this complex workflow pattern generate or preserve the expected revenue?"

**Example Test Structure**:
```python
def test_marketing_campaign_with_or_join_generates_revenue():
    # Arrange: Set up WCP-7 OR-Join workflow (email + social + paid ads)
    # Act: Execute workflow to completion (all paths must complete)
    # Assert: $50,000 in revenue is recognized from closed deals
    assert recognized_revenue >= 50_000
```

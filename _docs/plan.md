# Household Chore Bounty Board - MVP Scope Document

## 1. Project Overview
The Household Chore Bounty Board is a gamified task management web application designed to incentivize teenagers to complete household chores. By treating chores as "bounties" with point values, members can earn currency to spend in a "Perk Store." The system ensures accountability through parent-approved workflows and integrates seamlessly into the family's daily communication via Discord.

## 2. Technical Stack
*   **Backend Framework:** Django (Python)
*   **Frontend Interface:** Django Templates + HTMX (for dynamic, app-like interactions without heavy JavaScript)
*   **Database:** SQLite (Self-contained, perfect for an MVP and homework scope)
*   **Authentication:** Discord OAuth (Users log in with existing Discord accounts)
*   **Integrations:** Discord Webhooks (for system notifications)

## 3. User Roles
*   **Parent (Admin):** Can create bounties, set point values, approve completed chores, reject sloppy work, and fulfill purchased perks.
*   **Child (User):** Can view the bounty board, claim chores, submit proof of completion, and purchase items from the Perk Store.

## 4. Core Features & Mechanics

### 4.1. The Bounty Board & Task Creation
*   **Automated Weekly Reset:** A core set of recurring household chores automatically populates the board at the start of each week.
*   **Ad-Hoc Bounties:** Parents can manually add one-off chores to the board at any time.
*   **Surge Pricing (Basic Framework):** Chores will eventually feature point values that increase over time to incentivize unpopular tasks (specific math/algorithm deferred to post-MVP).

### 4.2. Claiming & Workflow
*   **Exclusive Lock:** When a user claims a bounty, it is exclusively reserved for them for a set time window (e.g., 2 hours). If the timer expires before submission, the chore returns to the public board.
*   **Submission:** Once completed, the user submits the chore via the dashboard for review.

### 4.3. Quality Control (Verification)
*   **Parent Approval:** Submitted chores enter a "Pending Review" state. Points are *only* awarded when a Parent clicks "Approve."
*   **The "Do Over" Protocol:** If a chore is done poorly, the Parent hits "Reject." The chore remains locked to the original user, who is prompted to redo and resubmit the work.

### 4.4. The Perk Store & Point Economy
*   **Individual Currency:** Users accrue points individually.
*   **Parent Fulfillment Queue:** When a user buys a perk (e.g., allowance cash, screen time, picking dinner), the points are temporarily locked. The Parent must physically fulfill the perk and click "Fulfill" on the dashboard before the points are permanently deducted from the user's balance.

### 4.5. Discord Integration
*   **Authentication:** Frictionless login using Discord credentials.
*   **Webhook Notifications:** The Django backend pushes real-time alerts to a designated family Discord channel for key events (e.g., "New ad-hoc bounty posted", "Chore pending approval", "Perk purchased").

## 5. Out of Scope for MVP (Future Enhancements)
*   Complex Surge Pricing algorithms (linear/exponential curves).
*   Photo uploads for chore verification.
*   Co-op/Multiplayer claiming mechanics.
*   Migration to a production database (PostgreSQL).

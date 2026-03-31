---
phase: 02-basket-and-product-management
plan: 02
subsystem: bot-handlers
tags: [aiogram, telegram, inline-keyboards, fsm, basket-crud]

requires:
  - phase: 02-01
    provides: "DB models, repositories, callbacks, keyboards, states, i18n strings for baskets"
provides:
  - "Basket CRUD handlers: /baskets, /new_basket, view, delete, switch active"
  - "FSM-based basket creation flow (name input + source selection)"
  - "Charts and Edit stub handlers for TXUX-02 compliance"
  - "Basket router registered in dispatcher"
affects: [02-03, 03-scheduling, 04-charts]

tech-stack:
  added: []
  patterns:
    - "Handler instantiates repository inline: BasketRepository(session)"
    - "FSM state stored in state.update_data, cleared after callback reads it"
    - "Callback handlers always end with await callback.answer()"

key-files:
  created:
    - src/price_spy/bot/handlers/basket.py
  modified:
    - src/price_spy/bot/create.py

key-decisions:
  - "Instantiate BasketRepository inside handlers rather than middleware injection (consistent with simple pattern, no basket middleware needed)"
  - "Charts and Edit buttons present as stubs with show_alert=True per TXUX-02"
  - "Viewing a basket automatically sets it as active per BSKT-03"

patterns-established:
  - "Callback handler pattern: filter by CallbackData subclass + F.action == value"
  - "FSM flow: set state -> receive text -> store in state data -> callback reads and clears"
  - "Guard pattern: check user is None -> show language keyboard -> return"

requirements-completed: [BSKT-01, BSKT-02, BSKT-03, BSKT-04, BSKT-05, TXUX-01, TXUX-02]

duration: 2min
completed: 2026-03-30
---

# Phase 02 Plan 02: Basket Handlers Summary

**Basket CRUD handlers with FSM creation flow, inline keyboard navigation, active-basket switching, and deletion with confirmation**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-30T22:53:05Z
- **Completed:** 2026-03-30T22:55:05Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments
- All basket CRUD handlers implemented: /baskets lists baskets, /new_basket starts creation flow
- FSM collects basket name then inline keyboard selects source (Arbuz/Magnum)
- Viewing a basket activates it and shows 7 action buttons (Items, Prices, Charts, Add, Edit, Delete, Back)
- Delete has two-step confirmation flow
- 10-basket limit enforced at creation with race condition guard on callback
- Charts and Edit stub handlers present per TXUX-02
- Basket router registered in dispatcher after start router

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement basket handlers and wire router** - `e173aa1` (feat)

## Files Created/Modified
- `src/price_spy/bot/handlers/basket.py` - All basket CRUD handlers (12 handlers: 2 commands, 1 FSM, 9 callbacks)
- `src/price_spy/bot/create.py` - Added basket router import and registration

## Decisions Made
- Instantiate BasketRepository inside each handler rather than via middleware injection -- keeps it simple and consistent since no basket middleware exists
- Charts and Edit buttons are stub handlers with `show_alert=True` -- present in UI per TXUX-02 but not functional until Phase 4
- Viewing/selecting a basket automatically sets it as active (per BSKT-03)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Known Stubs
- `src/price_spy/bot/handlers/basket.py` line ~281: `callback_charts_stub` -- shows "coming soon" alert, intentional per TXUX-02, resolved in Phase 4
- `src/price_spy/bot/handlers/basket.py` line ~292: `callback_edit_stub` -- shows "edit quantity" alert, intentional stub, resolved in future plan

## Next Phase Readiness
- Basket handlers complete, ready for product/item handlers (Plan 02-03)
- Basket router is registered before product router position (Pitfall 5 compliance)
- Active basket switching enables product addition flow in Plan 02-03

---
*Phase: 02-basket-and-product-management*
*Completed: 2026-03-30*

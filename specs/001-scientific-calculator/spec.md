# Feature Specification: Scientific Calculator

**Feature Branch**: `001-scientific-calculator`

**Created**: 2026-11-17

**Status**: Draft

**Input**: User description: "Build a scientific calculator application that provides accurate and intuitive mathematical calculations through a clean user interface, supporting basic arithmetic, scientific functions, trigonometry with Degree/Radian modes, constants, expression review, history, error handling, and keyboard/mouse usability."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Evaluate arithmetic expressions (Priority: P1)

A user builds an expression such as `2 + 3 × 4` using buttons or the keyboard, reviews the complete expression, and evaluates it to get `14`. The expression and result stay separately visible.

**Why this priority**: This is the calculator's core job and the minimum viable product.

**Independent Test**: Enter each arithmetic example by mouse and keyboard and compare the displayed result.

**Acceptance Scenarios**:

1. **Given** `2 + 3 × 4`, **When** evaluated, **Then** the result is `14`.
2. **Given** `(2 + 3) × 4`, **When** evaluated, **Then** the result is `20`.
3. **Given** `-5 + 2`, **When** evaluated, **Then** the result is `-3`.
4. **Given** a partial expression, **When** Delete or Clear is pressed, **Then** the expression updates or empties as expected.

---

### User Story 2 - Recover safely from invalid input (Priority: P2)

A user enters `5 / 0` or a malformed expression. The calculator shows a clear message, keeps the expression for correction, and remains usable.

**Why this priority**: A calculator that crashes or loses work on bad input is unusable.

**Independent Test**: Submit each error case, then correct it and evaluate successfully.

**Acceptance Scenarios**:

1. **Given** `5 / 0`, **When** evaluated, **Then** a clear error is shown and the calculator remains operational.
2. **Given** `sqrt(-1)`, `log(0)`, or `log(-5)`, **When** evaluated, **Then** an out-of-domain error is shown.
3. **Given** `2 +` or `(2+3`, **When** evaluated, **Then** an invalid-expression error is shown.
4. **Given** an error is showing, **When** the user edits and re-evaluates, **Then** a correct result appears.

---

### User Story 3 - Use scientific functions and constants (Priority: P3)

A user computes square roots, squares, powers, exponentials, logarithms, and absolute values, and inserts π or e into an expression.

**Why this priority**: These functions are what distinguish a scientific calculator from a basic one.

**Independent Test**: Evaluate one representative expression per function and constant.

**Acceptance Scenarios**:

1. **Given** `sqrt(16)`, **When** evaluated, **Then** the result is `4`.
2. **Given** `2^8` or `x²` applied to `7`, **When** evaluated, **Then** the results are `256` and `49`.
3. **Given** `ln(e)`, `log(1000)`, and `abs(-7)`, **When** evaluated, **Then** the results are `1`, `3`, and `7`.
4. **Given** π is inserted, **When** displayed, **Then** it is the double-precision value `math.pi`, rendered by the app's shared 12-significant-digit formatter.

---

### User Story 4 - Trigonometry with a visible angle mode (Priority: P4)

A user selects Degrees or Radians, always sees the active mode, and evaluates trigonometric and inverse trigonometric functions.

**Why this priority**: Trigonometry is required, and a hidden or implicit mode produces confidently wrong answers.

**Independent Test**: Evaluate the same trig expression in both modes and switch modes between evaluations.

**Acceptance Scenarios**:

1. **Given** Degree mode and `sin(30)`, **When** evaluated, **Then** the result is `0.5`.
2. **Given** Radian mode and `sin(π/2)`, **When** evaluated, **Then** the result is `1`.
3. **Given** Degree mode and `asin(0.5)`, **When** evaluated, **Then** the result is `30`.
4. **Given** the mode changes, **Then** the mode indicator updates and later evaluations use the new mode.

---

### User Story 5 - Review calculation history (Priority: P5)

After several evaluations, the user reviews recent expressions and results, newest first.

**Why this priority**: History makes repeated work easier but is not needed for first use.

**Independent Test**: Evaluate three expressions and verify all three appear in order.

**Acceptance Scenarios**:

1. **Given** three successful evaluations, **When** history is viewed, **Then** all three appear newest first as `expression = result`.
2. **Given** a trigonometric calculation, **When** it appears in history, **Then** its angle mode is recorded.
3. **Given** a failed evaluation, **Then** it is not added to history.

### Edge Cases

- Unary minus versus exponentiation: `-2^2` equals `-4`; parentheses override.
- Exponentiation is right-associative: `2^3^2` equals `512`.
- `tan(90°)` and `asin(2)` are out of domain and show errors.
- An empty expression is not evaluated.
- A trailing operator or mismatched parentheses shows an error.
- Very large results report an overflow error; very small results display as zero.
- A second decimal point in one number is prevented.
- History is capped so it cannot grow without bound.

## Requirements *(mandatory)*

### Functional Requirements

**Arithmetic**

- **FR-001**: Users MUST enter integers, decimals, negative numbers, and parentheses.
- **FR-002**: The calculator MUST apply standard precedence: exponentiation, then × and ÷, then + and −; parentheses override.
- **FR-003**: `+ − × ÷` and `x²`, `xʸ` MUST be available, with decimal point and sign change controls.
- **FR-004**: The full expression MUST stay visible while it is built and after evaluation.
- **FR-005**: Expression and result MUST be displayed as clearly separate areas.
- **FR-006**: C MUST clear the current expression; Delete MUST remove the last entry; `=` MUST evaluate.

**Scientific functions and constants**

- **FR-007**: The calculator MUST provide square root, `x²`, `xʸ`, `eˣ`, natural log (ln), base-10 log (log), and absolute value.
- **FR-008**: Functions MUST accept expressions as arguments and MUST be nestable.
- **FR-009**: π and e MUST be insertable anywhere a number is allowed.
- **FR-010**: Exponentiation MUST be right-associative (`2^3^2` equals `512`), and unary minus MUST bind less tightly than exponentiation (`-2^2` equals `-4`).

**Trigonometry**

- **FR-011**: The calculator MUST provide sin, cos, tan, and their inverses.
- **FR-012**: Every trigonometric evaluation MUST use exactly one explicitly selected mode, Degrees or Radians, with Degrees as the default.
- **FR-013**: The active angle mode MUST be visible at all times without user action.
- **FR-014**: Inverse trigonometric results MUST be expressed in the active mode.

**Results and errors**

- **FR-015**: Results MUST show up to 12 significant digits, omit unnecessary trailing zeros, and never show negative zero.
- **FR-016**: Division by zero MUST produce a clear error and leave the calculator operational.
- **FR-017**: Real-domain violations MUST produce clear errors: `sqrt` of a negative, `log` of zero or a negative, `asin`/`acos` outside −1 to 1, and undefined tangents.
- **FR-018**: Malformed or incomplete expressions MUST produce a clear, non-technical error without exposing internals.
- **FR-019**: After any error, the expression MUST remain editable and re-evaluable.

**History and usability**

- **FR-020**: Each successful evaluation MUST be recorded with its expression and result. When the evaluation used any angle-aware operation, the active angle mode MUST also be recorded; the calculation layer MUST report whether an evaluation was angle-aware so the interface never has to infer it.
- **FR-021**: History MUST show newest first and retain the most recent 50 entries for the session.
- **FR-022**: Basic and scientific controls MUST be visually separate groups, with numbers, arithmetic, scientific functions, and evaluation controls distinguished.
- **FR-023**: Every control MUST be usable by mouse and keyboard, with visible feedback on activation and visible keyboard focus.
- **FR-024**: The interface MUST remain usable at 375, 768, and 1440 pixel widths.
- **FR-025**: The calculator MUST prevent or resolve adjacent operands that have no operator (for example `2π`, `π2`, `2 3`, `2sin(30)`), so an ambiguous expression is never evaluated as written.
- **FR-026**: Existing successful calculation results, both request shapes, every operator alias, and the response's `result` field MUST remain unchanged. Error presentation is governed by FR-018 and FR-019 and may be refined.

### Key Entities

- **Expression**: The sequence of numbers, operators, functions, constants, and parentheses the user builds, plus the angle mode used at evaluation.
- **Calculation Result**: Either a formatted numeric value or a user-facing error, linked to its expression and angle mode.
- **History Entry**: A successful expression, its result, the angle mode where relevant, and its order in the list.
- **Angle Mode Setting**: The active Degrees or Radians choice; Degrees by default; retained for the session.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of the acceptance examples produce exactly the stated results.
- **SC-002**: 100% of the listed error cases produce a visible, understandable message, with no unhandled failure and the calculator still usable afterward.
- **SC-003**: Results agree with a standard scientific calculator to at least 12 significant digits across the supported functions.
- **SC-004**: A user can enter and evaluate a 15-entry expression in under 30 seconds using only the mouse or only the keyboard.
- **SC-005**: The active angle mode is identifiable without any interaction in 100% of evaluations.
- **SC-006**: The last 50 successful calculations remain reviewable for the session, newest first.
- **SC-007**: 100% of controls are reachable and operable by keyboard, and the classical calculator's existing results are unchanged.

## Assumptions

- Calculations are real-number only; complex results are out of scope and out-of-domain inputs are errors.
- The scientific calculator extends the existing calculator experience rather than replacing it; basic operations remain immediately accessible.
- History is session-only, newest first, capped at 50, and excludes failed evaluations.
- Results use up to 12 significant digits with scientific notation for very large or very small magnitudes.
- "Exponential functions" means `eˣ`; general exponentiation is provided by `xʸ`.
- Out of scope: graphing, matrices, complex numbers, unit conversion, memory registers, and history export.

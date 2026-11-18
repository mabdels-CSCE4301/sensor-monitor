const display = document.getElementById('display');
const expressionEl = document.getElementById('expression');
const buttons = document.querySelectorAll('button');
const keypadButtons = document.querySelectorAll('.keys button');
const calculator = document.getElementById('calculator');
const status = document.getElementById('calc-status');
const skinSelect = document.getElementById('skin-select');
const angleIndicator = document.getElementById('angle-mode-indicator');
const historyList = document.getElementById('history-list');
const historyEmpty = document.getElementById('history-empty');

// The <option> list in index.html is the single registry of available skins.
const SKINS = skinSelect
  ? Array.from(skinSelect.options).map((option) => option.value)
  : ['default'];
const SKIN_STORAGE_KEY = 'calculator-skin';

const HISTORY_LIMIT = 50;
const ANGLE_MODES = ['DEG', 'RAD'];
const TRAILING_OPERATOR = /[+\-*/%^]$/;
const TRAILING_OPERAND = /(\d+\.?\d*|pi|e|\))$/;

const state = {
  currentInput: '0',
  expression: '',
  waitingForNewValue: false,
  resultShown: false,
  isError: false,
  isLoading: false,
  errorMessage: '',
  pendingMultiply: false,
  angleMode: 'DEG',
  history: [],
  // 'auto' = inserted by a function key (may be auto-closed); 'user' = explicit.
  parens: [],
};

function updateDisplay() {
  display.textContent = state.isError ? state.errorMessage : state.currentInput;
  expressionEl.textContent = state.expression || '0';
  display.classList.toggle('is-error', state.isError);
}

function setKeysDisabled(disabled) {
  keypadButtons.forEach((button) => {
    button.disabled = disabled;
  });
}

function announce(message) {
  if (status) {
    status.textContent = message;
  }
}

/* Shared expression helpers. */

function endsWithOperand(text) {
  return /(\d|\.|\))$/.test(text) || /(pi|e)$/.test(text);
}

function trailingOperand(text) {
  if (!text) return '0';
  if (TRAILING_OPERATOR.test(text)) return text.slice(-1);
  const match = text.match(TRAILING_OPERAND);
  return match ? match[0] : '0';
}

/* Close function parentheses only; explicit user parentheses must stay open so
   an incomplete expression such as "(2+3" still reports an error. */
function closeOpenParens() {
  while (
    state.parens.length > 0 &&
    state.parens[state.parens.length - 1] === 'auto' &&
    endsWithOperand(state.expression)
  ) {
    state.expression += ')';
    state.parens.pop();
  }
}

function beginEdit() {
  if (state.isError) {
    state.isError = false;
    state.errorMessage = '';
  }
}

/* Input handlers. */

function inputDigit(value) {
  beginEdit();

  if (state.resultShown) {
    state.expression = value;
    state.currentInput = value;
    state.resultShown = false;
    state.waitingForNewValue = false;
    state.pendingMultiply = false;
    state.parens = [];
    updateDisplay();
    return;
  }

  if (state.waitingForNewValue) {
    state.currentInput = value;
    state.expression += (state.pendingMultiply ? '*' : '') + value;
    state.pendingMultiply = false;
    state.waitingForNewValue = false;
  } else if (state.currentInput === '0') {
    state.currentInput = value;
    state.expression = state.expression
      ? state.expression.slice(0, -1) + value
      : value;
  } else {
    state.currentInput += value;
    state.expression = state.expression ? state.expression + value : value;
  }
  updateDisplay();
}

function inputDecimal() {
  beginEdit();

  if (state.resultShown) {
    state.currentInput = '0.';
    state.expression = '0.';
    state.resultShown = false;
    state.waitingForNewValue = false;
    state.pendingMultiply = false;
    state.parens = [];
  } else if (state.waitingForNewValue) {
    state.currentInput = '0.';
    state.expression += (state.pendingMultiply ? '*' : '') + '0.';
    state.pendingMultiply = false;
    state.waitingForNewValue = false;
  } else if (!state.currentInput.includes('.')) {
    state.currentInput += '.';
    state.expression = state.expression ? state.expression + '.' : '0.';
  }
  updateDisplay();
}

function inputOperator(operator) {
  beginEdit();

  if (state.resultShown) {
    state.expression = state.currentInput;
    state.resultShown = false;
    state.parens = [];
  }

  if (state.expression && TRAILING_OPERATOR.test(state.expression)) {
    state.expression = state.expression.slice(0, -1) + operator;
  } else if (state.expression) {
    state.expression += operator;
  } else {
    state.expression = operator;
  }

  state.currentInput =
    operator === '*' ? '×' : operator === '/' ? '÷' : operator === '-' ? '−' : operator;
  state.waitingForNewValue = true;
  state.pendingMultiply = false;
  updateDisplay();
}

function inputParen(paren) {
  beginEdit();

  if (paren === '(') {
    if (state.resultShown) {
      state.expression = '';
      state.resultShown = false;
      state.parens = [];
    }
    if (state.expression && endsWithOperand(state.expression)) {
      state.expression += '*';
    }
    state.expression += '(';
    state.parens.push('user');
    state.currentInput = '(';
    state.waitingForNewValue = true;
    state.pendingMultiply = false;
  } else if (state.expression && endsWithOperand(state.expression)) {
    state.expression += ')';
    state.parens.pop();
    state.currentInput = ')';
    state.waitingForNewValue = false;
    state.pendingMultiply = false;
  }
  updateDisplay();
}

function insertFunction(token) {
  beginEdit();

  if (state.expression && endsWithOperand(state.expression)) {
    state.expression += '*';
  }
  state.expression += token;
  state.parens.push('auto');
  state.currentInput = token;
  state.waitingForNewValue = true;
  state.pendingMultiply = false;
  state.resultShown = false;
  updateDisplay();
}

function insertConstant(token, symbol) {
  beginEdit();

  if (state.expression && endsWithOperand(state.expression)) {
    state.expression += '*';
  }
  state.expression += token;
  state.currentInput = symbol;
  state.waitingForNewValue = true;
  state.pendingMultiply = true;
  state.resultShown = false;
  updateDisplay();
}

function applySquare() {
  beginEdit();

  if (state.resultShown) {
    state.expression = state.currentInput;
    state.resultShown = false;
    state.parens = [];
  }
  if (!state.expression || !endsWithOperand(state.expression)) {
    return;
  }
  state.expression += '^2';
  state.currentInput = '^2';
  state.waitingForNewValue = true;
  state.pendingMultiply = false;
  updateDisplay();
}

function toggleSign() {
  beginEdit();

  if (!state.expression) {
    state.expression = '-';
    state.currentInput = '-';
    state.waitingForNewValue = true;
    updateDisplay();
    return;
  }

  const match = state.expression.match(TRAILING_OPERAND);
  if (!match) return;

  const start = state.expression.length - match[0].length;
  const before = state.expression.slice(0, start);
  const prefix = before.slice(0, -1);

  if (before.endsWith('-') && (!prefix || TRAILING_OPERATOR.test(prefix) || prefix.endsWith('('))) {
    state.expression = prefix + match[0];
  } else {
    state.expression = before + '-' + match[0];
  }
  state.currentInput = trailingOperand(state.expression);
  state.waitingForNewValue = false;
  state.pendingMultiply = false;
  updateDisplay();
}

function clearAll() {
  state.currentInput = '0';
  state.expression = '';
  state.waitingForNewValue = false;
  state.resultShown = false;
  state.isError = false;
  state.errorMessage = '';
  state.pendingMultiply = false;
  state.parens = [];
  updateDisplay();
}

function deleteLast() {
  beginEdit();

  if (!state.expression) {
    return;
  }

  state.resultShown = false;
  state.pendingMultiply = false;
  const removed = state.expression.slice(-1);
  state.expression = state.expression.slice(0, -1);

  if (removed === '(') {
    state.parens.pop();
  } else if (removed === ')') {
    state.parens.push('user');
  }

  if (!state.expression) {
    state.currentInput = '0';
    state.waitingForNewValue = false;
  } else if (TRAILING_OPERATOR.test(state.expression)) {
    const operator = state.expression.slice(-1);
    state.currentInput = operator === '*' ? '×' : operator === '/' ? '÷' : operator;
    state.waitingForNewValue = true;
  } else {
    state.currentInput = trailingOperand(state.expression);
    state.waitingForNewValue = false;
  }
  updateDisplay();
}

/* Angle mode. */

function setAngleMode(mode, { announce: shouldAnnounce = true } = {}) {
  if (!ANGLE_MODES.includes(mode)) return;
  state.angleMode = mode;
  document.querySelectorAll('.angle-option').forEach((button) => {
    button.setAttribute('aria-pressed', String(button.dataset.angleMode === mode));
  });
  if (angleIndicator) {
    angleIndicator.textContent = mode;
  }
  if (shouldAnnounce) {
    announce(`Angle mode ${mode}`);
  }
}

/* History. */

function renderHistory() {
  if (!historyList) return;
  historyList.textContent = '';

  // Newest first: keep insertion order in state, render backwards.
  [...state.history].reverse().forEach((entry) => {
    const item = document.createElement('li');
    item.className = 'history-entry';

    const expression = document.createElement('span');
    expression.className = 'history-expression';
    expression.textContent = entry.expression;

    const result = document.createElement('span');
    result.className = 'history-result';
    result.textContent = entry.display;

    item.append(expression, document.createTextNode(' = '), result);

    if (entry.angleMode) {
      const mode = document.createElement('span');
      mode.className = 'history-mode';
      mode.textContent = entry.angleMode;
      item.append(' ', mode);
    }

    historyList.append(item);
  });

  if (historyEmpty) {
    historyEmpty.hidden = state.history.length > 0;
  }
}

function addHistory(expression, data) {
  const displayValue =
    data.display !== undefined ? String(data.display) : String(data.result);
  state.history.push({
    expression,
    display: displayValue,
    angleMode: data.is_trigonometric === true ? data.angle_mode : null,
  });
  if (state.history.length > HISTORY_LIMIT) {
    state.history.splice(0, state.history.length - HISTORY_LIMIT);
  }
  renderHistory();
}

/* Evaluation. */

async function evaluateExpression() {
  if (state.isLoading) return;

  closeOpenParens();
  const rawExpression = state.expression.replace(/×/g, '*').replace(/÷/g, '/');
  if (!rawExpression) return;

  state.isLoading = true;
  state.isError = false;
  state.errorMessage = '';
  // Disable the keypad while the request is in flight so no click can mutate
  // state that the response would then overwrite.
  setKeysDisabled(true);
  calculator.setAttribute('aria-busy', 'true');
  calculator.dataset.loading = 'true';

  try {
    const params = new URLSearchParams({
      expression: rawExpression,
      angle_mode: state.angleMode,
    });
    const response = await fetch(`/api/calc?${params.toString()}`);
    const data = await response.json();

    if (!response.ok || data.success === false) {
      throw new Error(data.detail || 'Calculation failed');
    }

    state.currentInput =
      data.display !== undefined ? String(data.display) : String(data.result);
    state.waitingForNewValue = true;
    state.resultShown = true;
    state.isError = false;
    state.pendingMultiply = false;
    updateDisplay();
    announce(`Result ${state.currentInput}`);
    addHistory(rawExpression, data);
  } catch (error) {
    state.isError = true;
    state.errorMessage = error.message || 'Calculation failed';
    state.currentInput = trailingOperand(state.expression);
    state.waitingForNewValue = TRAILING_OPERATOR.test(state.expression);
    state.resultShown = false;
    updateDisplay();
    announce(`Error: ${state.errorMessage}`);
  } finally {
    state.isLoading = false;
    setKeysDisabled(false);
    calculator.setAttribute('aria-busy', 'false');
    calculator.dataset.loading = 'false';
  }
}

/* Controls. */

buttons.forEach((button) => {
  button.addEventListener('click', (event) => {
    // Pointer clicks leave focus on the key, which would make a later physical
    // Enter re-activate that key instead of evaluating. Keyboard activation
    // (event.detail === 0) keeps focus for native Enter/Space behavior.
    if (event.detail > 0) {
      button.blur();
    }

    if (button.dataset.angleMode) {
      setAngleMode(button.dataset.angleMode);
      return;
    }

    if (button.id === 'clear-history') {
      state.history = [];
      renderHistory();
      announce('History cleared');
      return;
    }

    const value = button.dataset.value;
    if (value === undefined) return;

    if (!isNaN(Number(value)) || value === '.') {
      if (value === '.') {
        inputDecimal();
      } else {
        inputDigit(value);
      }
      return;
    }

    switch (value) {
      case 'C':
        clearAll();
        break;
      case 'DEL':
        deleteLast();
        break;
      case '=':
        evaluateExpression();
        break;
      case '±':
        toggleSign();
        break;
      case 'x²':
        applySquare();
        break;
      case 'xʸ':
        inputOperator('^');
        break;
      case 'π':
        insertConstant('pi', 'π');
        break;
      case 'e':
        insertConstant('e', 'e');
        break;
      case '(':
      case ')':
        inputParen(value);
        break;
      default:
        if (value.endsWith('(')) {
          insertFunction(value);
        } else {
          inputOperator(value);
        }
        break;
    }
  });
});

/* Physical-keyboard support. */

const KEY_VALUES = {
  0: '0',
  1: '1',
  2: '2',
  3: '3',
  4: '4',
  5: '5',
  6: '6',
  7: '7',
  8: '8',
  9: '9',
  '+': '+',
  '-': '-',
  '*': '*',
  '/': '/',
  '%': '%',
  '.': '.',
  '(': '(',
  ')': ')',
  '^': 'xʸ',
  '=': '=',
  Enter: '=',
  Escape: 'C',
  Backspace: 'DEL',
  Delete: 'C',
};

function isTypingTarget(target) {
  if (!(target instanceof Element)) return false;
  const tag = target.tagName;
  return tag === 'INPUT' || tag === 'SELECT' || tag === 'TEXTAREA' || target.isContentEditable;
}

document.addEventListener('keydown', (event) => {
  if (event.ctrlKey || event.metaKey || event.altKey) return;
  if (isTypingTarget(event.target)) return;

  // Let Enter/Space activate a focused button natively instead of remapping it.
  if (event.target instanceof HTMLButtonElement && (event.key === 'Enter' || event.key === ' ')) {
    return;
  }

  const value = KEY_VALUES[event.key];
  if (!value) return;

  const button = document.querySelector(`button[data-value="${value}"]`);
  if (!button) return;

  event.preventDefault();
  button.click();
});

/* Skin switching: <select> + localStorage + ?skin= deep links. */

function normalizeSkin(value) {
  return SKINS.includes(value) ? value : 'default';
}

function applySkin(value, { persist = false, updateUrl = false } = {}) {
  const skin = normalizeSkin(value);
  document.documentElement.setAttribute('data-skin', skin);

  if (skinSelect) {
    skinSelect.value = skin;
  }

  if (persist) {
    try {
      window.localStorage.setItem(SKIN_STORAGE_KEY, skin);
    } catch (storageError) {
      // Storage can be unavailable (private mode); the theme still applies.
    }
  }

  if (updateUrl) {
    const url = new URL(window.location.href);
    if (skin === 'default') {
      url.searchParams.delete('skin');
    } else {
      url.searchParams.set('skin', skin);
    }
    window.history.replaceState(null, '', url);
  }
}

if (skinSelect) {
  applySkin(document.documentElement.getAttribute('data-skin'));
  skinSelect.addEventListener('change', (event) => {
    applySkin(event.target.value, { persist: true, updateUrl: true });
  });
}

setAngleMode(state.angleMode, { announce: false });
renderHistory();
updateDisplay();

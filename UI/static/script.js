const display = document.getElementById('display');
const expression = document.getElementById('expression');
const buttons = document.querySelectorAll('button');
const calculator = document.getElementById('calculator');
const status = document.getElementById('calc-status');
const skinSelect = document.getElementById('skin-select');

// The <option> list in index.html is the single registry of available skins.
const SKINS = skinSelect
  ? Array.from(skinSelect.options).map((option) => option.value)
  : ['default'];
const SKIN_STORAGE_KEY = 'calculator-skin';

const state = {
  currentInput: '0',
  expression: '',
  waitingForNewValue: false,
  resultShown: false,
  isError: false,
  isLoading: false,
};

// The error auto-clear is scheduled here so fresh input can cancel it.
let errorResetTimer = null;

function cancelErrorReset() {
  if (errorResetTimer !== null) {
    clearTimeout(errorResetTimer);
    errorResetTimer = null;
  }
}

function updateDisplay() {
  display.textContent = state.currentInput;
  expression.textContent = state.expression || '0';
  display.classList.toggle('is-error', state.isError);
}

function setKeysDisabled(disabled) {
  buttons.forEach((button) => {
    button.disabled = disabled;
  });
}

function announce(message) {
  if (status) {
    status.textContent = message;
  }
}

function inputDigit(value) {
  cancelErrorReset();
  if (state.isError) return;

  if (state.resultShown) {
    state.expression = value;
    state.currentInput = value;
    state.resultShown = false;
    state.waitingForNewValue = false;
    updateDisplay();
    return;
  }

  if (state.waitingForNewValue) {
    state.currentInput = value;
    state.expression += value;
    state.waitingForNewValue = false;
  } else if (state.currentInput === '0') {
    // Replace the leading zero in both strings so "05" never reaches the API.
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
  cancelErrorReset();
  if (state.isError) return;

  if (state.resultShown) {
    state.currentInput = '0.';
    state.expression = '0.';
    state.resultShown = false;
    state.waitingForNewValue = false;
  } else if (state.waitingForNewValue) {
    state.currentInput = '0.';
    state.waitingForNewValue = false;
    state.expression = (state.expression || '') + '0.';
  } else if (!state.currentInput.includes('.')) {
    state.currentInput += '.';
    state.expression = state.expression ? state.expression + '.' : '0.';
  }
  updateDisplay();
}

function inputOperator(operator) {
  cancelErrorReset();
  if (state.isError) return;

  state.resultShown = false;
  if (state.expression && /[+\-*/%]$/.test(state.expression)) {
    state.expression = state.expression.slice(0, -1) + operator;
  } else {
    state.expression += operator;
  }
  state.currentInput = operator === '*' ? '×' : operator === '/' ? '÷' : operator;
  state.waitingForNewValue = true;
  updateDisplay();
}

function clearAll() {
  cancelErrorReset();
  state.currentInput = '0';
  state.expression = '';
  state.waitingForNewValue = false;
  state.resultShown = false;
  state.isError = false;
  updateDisplay();
}

function deleteLast() {
  cancelErrorReset();
  if (state.isError) return;

  state.resultShown = false;
  if (!state.expression) {
    return;
  }

  state.expression = state.expression.slice(0, -1);

  if (!state.expression) {
    state.currentInput = '0';
    state.waitingForNewValue = false;
  } else if (/[+\-*/%]$/.test(state.expression)) {
    // Trailing operator: show it and let the next digit start a new operand.
    const operator = state.expression.slice(-1);
    state.currentInput = operator === '*' ? '×' : operator === '/' ? '÷' : operator;
    state.waitingForNewValue = true;
  } else {
    // Otherwise the display mirrors the operand after the last operator.
    state.currentInput = state.expression.match(/[^+\-*/%]*$/)[0] || '0';
    state.waitingForNewValue = false;
  }
  updateDisplay();
}

async function evaluateExpression() {
  if (state.isError || state.isLoading) return;

  const rawExpression = state.expression.replace(/×/g, '*').replace(/÷/g, '/');
  if (!rawExpression) return;

  cancelErrorReset();
  state.isLoading = true;
  // Disable the keypad while the request is in flight so no click can mutate
  // state that the response would then overwrite.
  setKeysDisabled(true);
  calculator.setAttribute('aria-busy', 'true');
  calculator.dataset.loading = 'true';

  try {
    const response = await fetch(`/api/calc?expression=${encodeURIComponent(rawExpression)}`);
    const data = await response.json();

    if (!response.ok || !data.success) {
      throw new Error(data.detail || 'Calculation failed');
    }

    state.currentInput = String(data.result);
    state.expression = String(data.result);
    state.waitingForNewValue = true;
    state.resultShown = true;
    state.isError = false;
    updateDisplay();
    announce(`Result ${data.result}`);
  } catch (error) {
    state.currentInput = 'Error';
    state.expression = 'invalid';
    state.waitingForNewValue = true;
    state.resultShown = false;
    state.isError = true;
    updateDisplay();
    announce(`Error: ${error.message || 'Calculation failed'}`);
    cancelErrorReset();
    errorResetTimer = setTimeout(() => {
      errorResetTimer = null;
      clearAll();
    }, 800);
  } finally {
    state.isLoading = false;
    setKeysDisabled(false);
    calculator.setAttribute('aria-busy', 'false');
    calculator.dataset.loading = 'false';
  }
}

buttons.forEach((button) => {
  button.addEventListener('click', (event) => {
    const value = button.dataset.value;

    // Pointer clicks leave focus on the key, which would make a later physical
    // Enter re-activate that key instead of evaluating. Keyboard activation
    // (event.detail === 0) keeps focus for native Enter/Space behavior.
    if (event.detail > 0) {
      button.blur();
    }

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
      default:
        inputOperator(value);
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

updateDisplay();

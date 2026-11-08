const display = document.getElementById('display');
const expression = document.getElementById('expression');
const buttons = document.querySelectorAll('button');

const state = {
  currentInput: '0',
  expression: '',
  waitingForNewValue: false,
};

function updateDisplay() {
  display.textContent = state.currentInput;
  expression.textContent = state.expression || '0';
}

function inputDigit(value) {
  if (state.waitingForNewValue) {
    state.currentInput = value;
    state.waitingForNewValue = false;
  } else {
    state.currentInput = state.currentInput === '0' ? value : state.currentInput + value;
  }
  state.expression = state.expression ? state.expression + value : value;
  updateDisplay();
}

function inputDecimal() {
  if (state.waitingForNewValue) {
    state.currentInput = '0.';
    state.waitingForNewValue = false;
    state.expression = (state.expression || '') + '0.';
  } else if (!state.currentInput.includes('.')) {
    state.currentInput += '.';
    state.expression = (state.expression || '') + '.';
  }
  updateDisplay();
}

function inputOperator(operator) {
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
  state.currentInput = '0';
  state.expression = '';
  state.waitingForNewValue = false;
  updateDisplay();
}

function deleteLast() {
  if (state.expression.length > 0) {
    state.expression = state.expression.slice(0, -1);
    state.currentInput = state.expression || '0';
    if (!state.expression) {
      state.currentInput = '0';
    }
    updateDisplay();
  }
}

async function evaluateExpression() {
  const rawExpression = state.expression.replace(/×/g, '*').replace(/÷/g, '/');
  if (!rawExpression) return;

  try {
    const response = await fetch(`/api/calc?expression=${encodeURIComponent(rawExpression)}`);
    const data = await response.json();

    if (!response.ok || !data.success) {
      throw new Error(data.detail || 'Calculation failed');
    }

    state.currentInput = String(data.result);
    state.expression = String(data.result);
    state.waitingForNewValue = true;
    updateDisplay();
  } catch (error) {
    state.currentInput = 'Error';
    state.expression = 'invalid';
    updateDisplay();
    setTimeout(() => {
      clearAll();
    }, 800);
  }
}

buttons.forEach((button) => {
  button.addEventListener('click', () => {
    const value = button.dataset.value;

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

updateDisplay();

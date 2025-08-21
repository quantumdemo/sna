document.addEventListener('DOMContentLoaded', function() {
    const calculatorWidget = document.getElementById('calculator');
    const toggleBtn = document.getElementById('calculator-toggle-btn');

    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => {
            if (window.innerWidth <= 768) {
                calculatorWidget.classList.toggle('open');
            } else {
                const isDisplayed = calculatorWidget.style.display === 'block';
                calculatorWidget.style.display = isDisplayed ? 'none' : 'block';
            }
        });
    }

    if (calculatorWidget) {
        const display = document.getElementById('calc-display');
        const historyDisplay = document.getElementById('calc-history');
        let currentValue = '';
        let operator = '';
        let previousValue = '';
        let history = '';

        calculatorWidget.addEventListener('click', function(e) {
            if (!e.target.matches('.calc-btn')) return;

            const key = e.target.dataset.key;
            const keyType = e.target.classList;

            if (keyType.contains('number')) {
                if (currentValue.length < 16) {
                    currentValue = currentValue === '0' ? key : currentValue + key;
                }
            } else if (key === '.') {
                if (!currentValue.includes('.')) {
                    currentValue += '.';
                }
            } else if (keyType.contains('operator') && key !== '=') {
                if (currentValue) {
                    operator = key;
                    previousValue = currentValue;
                    history = `${previousValue} ${getDisplayOperator(operator)}`;
                    currentValue = '';
                }
            } else if (key === '=') {
                if (operator && previousValue) {
                    history += ` ${currentValue} =`;
                    currentValue = String(eval(getEvalSafe(previousValue, operator, currentValue)));
                    operator = '';
                    previousValue = '';
                }
            } else if (key === '%') {
                history = `(${currentValue})%`;
                currentValue = String(parseFloat(currentValue) / 100);
            } else if (key === 'negate') {
                currentValue = String(parseFloat(currentValue) * -1);
            } else if (key === 'clear') {
                currentValue = '0';
                operator = '';
                previousValue = '';
                history = '';
            }
            updateDisplay();
        });

        function updateDisplay() {
            display.textContent = currentValue || previousValue || '0';
            historyDisplay.textContent = history;
            // Auto-adjust font size
            if (display.textContent.length > 10) {
                display.style.fontSize = '1.8rem';
            } else {
                display.style.fontSize = '2.5rem';
            }
        }

        function getDisplayOperator(op) {
            if (op === '*') return '×';
            if (op === '/') return '÷';
            return op;
        }

        function getEvalSafe(val1, op, val2) {
            // Basic security for eval
            const num1 = parseFloat(val1);
            const num2 = parseFloat(val2);
            if (isNaN(num1) || isNaN(num2)) return 0;
            switch(op) {
                case '+': return num1 + num2;
                case '-': return num1 - num2;
                case '*': return num1 * num2;
                case '/': return num1 / num2;
                default: return 0;
            }
        }

        // Make it draggable on desktop
        if (window.innerWidth > 768) {
            makeDraggable(calculatorWidget);
        }
    }

    function makeDraggable(element) {
        let pos1 = 0, pos2 = 0, pos3 = 0, pos4 = 0;
        const header = element.querySelector(".calculator-header");

        if (header) {
            header.onmousedown = dragMouseDown;
        }

        function dragMouseDown(e) {
            e = e || window.event;
            e.preventDefault();
            pos3 = e.clientX;
            pos4 = e.clientY;
            document.onmouseup = closeDragElement;
            document.onmousemove = elementDrag;
        }

        function elementDrag(e) {
            e = e || window.event;
            e.preventDefault();
            pos1 = pos3 - e.clientX;
            pos2 = pos4 - e.clientY;
            pos3 = e.clientX;
            pos4 = e.clientY;
            element.style.top = (element.offsetTop - pos2) + "px";
            element.style.left = (element.offsetLeft - pos1) + "px";
        }

        function closeDragElement() {
            document.onmouseup = null;
            document.onmousemove = null;
        }
    }
});

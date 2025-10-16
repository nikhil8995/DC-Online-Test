document.addEventListener('DOMContentLoaded', () => {
    const builder = document.getElementById('questionsBuilder');
    const addBtn = document.getElementById('addQuestionBtn');
    const form = document.getElementById('examForm');
    const hiddenJson = document.getElementById('questionsJson');

    if (!builder || !addBtn || !form || !hiddenJson) return;

    function createOptionInput(letter) {
        const wrap = document.createElement('div');
        wrap.className = 'option-row';
        wrap.innerHTML = `
      <label>${letter}) <input type="text" class="opt-input" data-letter="${letter}" placeholder="Option ${letter}" required /></label>
    `;
        return wrap;
    }

    function createQuestionCard(index) {
        const card = document.createElement('div');
        card.className = 'q-card card';
        card.dataset.index = index.toString();
        card.innerHTML = `
      <div class="q-head">
        <h4>Question <span class="q-num">${index + 1}</span></h4>
        <button type="button" class="btn ghost remove-q">Remove</button>
      </div>
      <label>Question text
        <input type="text" class="q-text" placeholder="Enter question" required />
      </label>
      <div class="grid-2">
        <div>
          <div class="opts"></div>
        </div>
        <div>
          <label>Correct answer (A/B/C/D)
            <select class="q-answer" required>
              <option value="">Select</option>
              <option value="A">A</option>
              <option value="B">B</option>
              <option value="C">C</option>
              <option value="D">D</option>
            </select>
          </label>
        </div>
      </div>
    `;
        const opts = card.querySelector('.opts');
        ['A', 'B', 'C', 'D'].forEach(letter => opts.appendChild(createOptionInput(letter)));
        card.querySelector('.remove-q').addEventListener('click', () => {
            card.remove();
            renumber();
        });
        return card;
    }

    function renumber() {
        [...builder.children].forEach((card, idx) => {
            card.dataset.index = idx.toString();
            const num = card.querySelector('.q-num');
            if (num) num.textContent = (idx + 1).toString();
        });
    }

    addBtn.addEventListener('click', () => {
        const idx = builder.children.length;
        builder.appendChild(createQuestionCard(idx));
        renumber();
    });

    form.addEventListener('submit', (e) => {
        // assemble questions array
        const questions = [];
        const cards = [...builder.children];
        if (cards.length === 0) {
            alert('Add at least one question.');
            e.preventDefault();
            return;
        }
        for (let i = 0; i < cards.length; i++) {
            const card = cards[i];
            const qText = card.querySelector('.q-text').value.trim();
            const answer = card.querySelector('.q-answer').value.trim();
            const optionInputs = card.querySelectorAll('.opt-input');
            const options = [];
            optionInputs.forEach(inp => {
                const letter = inp.dataset.letter;
                const text = inp.value.trim();
                options.push(`${letter}) ${text}`);
            });
            if (!qText || !answer || options.some(o => !o)) {
                alert('Please fill all question fields.');
                e.preventDefault();
                return;
            }
            questions.push({ id: i + 1, question: qText, options, answer });
        }
        hiddenJson.value = JSON.stringify(questions);
    });
});



(function () {
  const root = document.getElementById('character-builder');
  if (!root) {
    return;
  }

  const config = JSON.parse(document.getElementById('character-builder-config').textContent);
  const panel = document.getElementById('character-builder-panel');
  const stepsElement = document.getElementById('character-builder-steps');
  const errorElement = document.getElementById('character-builder-error');
  const backButton = document.getElementById('character-builder-back');
  const nextButton = document.getElementById('character-builder-next');
  const storageKey = 'dragonsire.character-builder.v1';
  const stepKeys = config.steps.map((step) => step.key);
  const defaultState = {
    currentStep: 0,
    name: '',
    race: '',
    gender: '',
    body_build: '',
    skin_tone: '',
    eye_color: '',
    hair_color: '',
    hair_style: '',
    nameValidation: { valid: false, pending: false, error: '' },
    submitting: false
  };

  let nameValidationTimer = null;
  let state = loadState();

  function getCookie(name) {
    const cookieValue = document.cookie
      .split(';')
      .map((entry) => entry.trim())
      .find((entry) => entry.startsWith(name + '='));
    return cookieValue ? decodeURIComponent(cookieValue.split('=').slice(1).join('=')) : '';
  }

  function loadState() {
    try {
      const parsed = JSON.parse(window.sessionStorage.getItem(storageKey) || '{}');
      return {
        ...defaultState,
        ...parsed,
        nameValidation: {
          ...defaultState.nameValidation,
          ...(parsed.nameValidation || {})
        }
      };
    } catch (error) {
      return { ...defaultState };
    }
  }

  function saveState() {
    window.sessionStorage.setItem(storageKey, JSON.stringify(state));
  }

  function clearError() {
    errorElement.hidden = true;
    errorElement.textContent = '';
  }

  function setError(message) {
    errorElement.hidden = !message;
    errorElement.textContent = message || '';
  }

  function setState(patch) {
    state = {
      ...state,
      ...patch,
      nameValidation: {
        ...state.nameValidation,
        ...(patch.nameValidation || {})
      }
    };
    saveState();
    render();
  }

  function getCurrentStepKey() {
    return stepKeys[state.currentStep] || stepKeys[0];
  }

  function validateCurrentStep() {
    const stepKey = getCurrentStepKey();
    if (stepKey === 'name') {
      return Boolean(state.nameValidation.valid) && !state.nameValidation.pending;
    }
    if (stepKey === 'race') {
      return Boolean(state.race);
    }
    if (stepKey === 'gender') {
      return Boolean(state.gender);
    }
    if (stepKey === 'skin-build') {
      return Boolean(state.skin_tone && state.body_build);
    }
    if (stepKey === 'hair-eyes') {
      return Boolean(state.hair_color && state.hair_style && state.eye_color);
    }
    return true;
  }

  function buildChoiceGrid(options, selectedValue, fieldName, descriptionBuilder, columnsClass) {
    const className = columnsClass ? `character-choice-grid ${columnsClass}` : 'character-choice-grid';
    return `
      <div class="${className}">
        ${options.map((option) => `
          <button type="button" class="character-choice-card${selectedValue === option.value ? ' is-selected' : ''}" data-choice-field="${fieldName}" data-choice-value="${option.value}">
            <span class="character-choice-card-label">${option.label}</span>
            ${descriptionBuilder ? `<span class="character-choice-card-copy">${descriptionBuilder(option)}</span>` : ''}
          </button>
        `).join('')}
      </div>
    `;
  }

  function renderNameStep() {
    const statusClass = state.nameValidation.error ? 'character-name-status is-error' : 'character-name-status';
    const statusText = state.nameValidation.pending
      ? 'Checking name availability...'
      : (state.nameValidation.error || (state.nameValidation.valid ? 'Name is available.' : 'Enter a valid character name.'));
    return `
      <div class="character-wizard-copy">
        <h2>Choose a character name.</h2>
        <p>This validates against the live Evennia character roster before you continue.</p>
      </div>
      <label class="character-form-field" for="character-builder-name">
        <span class="subpanel-title">Name</span>
        <input id="character-builder-name" class="character-name-input" type="text" maxlength="24" value="${escapeHtml(state.name)}" autocomplete="off">
        <span class="${statusClass}" id="character-builder-name-status">${escapeHtml(statusText)}</span>
      </label>
    `;
  }

  function renderRaceStep() {
    return `
      <div class="character-wizard-copy">
        <h2>Choose a race.</h2>
        <p>Race remains authoritative game data. This step only selects from the existing canonical list.</p>
      </div>
      ${buildChoiceGrid(config.options.races, state.race, 'race')}
    `;
  }

  function renderGenderStep() {
    return `
      <div class="character-wizard-copy">
        <h2>Choose a gender.</h2>
        <p>This uses the same canonical options already supported by the game.</p>
      </div>
      ${buildChoiceGrid(config.options.genders, state.gender, 'gender', null, 'is-three-up')}
    `;
  }

  function renderSkinBuildStep() {
    return `
      <div class="character-wizard-copy">
        <h2>Set body build and skin tone.</h2>
        <p>These are stored as structured appearance attributes on the Evennia character.</p>
      </div>
      <div class="character-review-grid">
        <div>
          <p class="subpanel-title">Body Build</p>
          ${buildChoiceGrid(config.options.body_builds, state.body_build, 'body_build')}
        </div>
        <div>
          <p class="subpanel-title">Skin Tone</p>
          ${buildChoiceGrid(config.options.skin_tones, state.skin_tone, 'skin_tone')}
        </div>
      </div>
    `;
  }

  function renderHairEyesStep() {
    return `
      <div class="character-wizard-copy">
        <h2>Set hair and eyes.</h2>
        <p>Hair color, hair style, and eye color finalize together so the review step reads cleanly.</p>
      </div>
      <div class="character-review-grid">
        <div>
          <p class="subpanel-title">Hair Color</p>
          ${buildChoiceGrid(config.options.hair_colors, state.hair_color, 'hair_color')}
        </div>
        <div>
          <p class="subpanel-title">Hair Style</p>
          ${buildChoiceGrid(config.options.hair_styles, state.hair_style, 'hair_style')}
        </div>
      </div>
      <div>
        <p class="subpanel-title">Eye Color</p>
        ${buildChoiceGrid(config.options.eye_colors, state.eye_color, 'eye_color', null, 'is-three-up')}
      </div>
    `;
  }

  function renderReviewStep() {
    const reviewFields = [
      ['Name', state.name],
      ['Race', labelFor(config.options.races, state.race)],
      ['Gender', labelFor(config.options.genders, state.gender)],
      ['Body Build', labelFor(config.options.body_builds, state.body_build)],
      ['Skin Tone', labelFor(config.options.skin_tones, state.skin_tone)],
      ['Hair Color', labelFor(config.options.hair_colors, state.hair_color)],
      ['Hair Style', labelFor(config.options.hair_styles, state.hair_style)],
      ['Eye Color', labelFor(config.options.eye_colors, state.eye_color)]
    ];
    return `
      <div class="character-wizard-copy">
        <h2>Review the character shell.</h2>
        <p>This will create the Evennia character, attach the identity data, and send the character through the existing first-play Empath Guild path.</p>
      </div>
      <div class="character-review-grid">
        ${reviewFields.map(([label, value]) => `
          <div class="character-review-card">
            <div class="character-review-label">${label}</div>
            <div class="character-review-value">${escapeHtml(value || '(unset)')}</div>
          </div>
        `).join('')}
      </div>
    `;
  }

  function renderStepContent() {
    const stepKey = getCurrentStepKey();
    if (stepKey === 'name') {
      return renderNameStep();
    }
    if (stepKey === 'race') {
      return renderRaceStep();
    }
    if (stepKey === 'gender') {
      return renderGenderStep();
    }
    if (stepKey === 'skin-build') {
      return renderSkinBuildStep();
    }
    if (stepKey === 'hair-eyes') {
      return renderHairEyesStep();
    }
    return renderReviewStep();
  }

  function renderSteps() {
    stepsElement.innerHTML = config.steps.map((step, index) => {
      const classes = ['character-wizard-step'];
      if (index === state.currentStep) {
        classes.push('is-active');
      }
      if (index < state.currentStep) {
        classes.push('is-complete');
      }
      return `<div class="${classes.join(' ')}"><strong>${index + 1}.</strong> ${step.label}</div>`;
    }).join('');
  }

  function renderButtons() {
    backButton.disabled = state.currentStep === 0 || state.submitting;
    nextButton.disabled = !validateCurrentStep() || state.submitting;
    nextButton.textContent = state.currentStep === stepKeys.length - 1 ? (state.submitting ? 'Creating...' : 'Create Character') : 'Continue';
  }

  function render() {
    renderSteps();
    panel.innerHTML = renderStepContent();
    renderButtons();
  }

  function labelFor(options, value) {
    const match = options.find((option) => option.value === value);
    return match ? match.label : value;
  }

  function escapeHtml(value) {
    return String(value || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  async function validateNameNow(name) {
    const trimmed = String(name || '').trim();
    if (!trimmed) {
      setState({ name: trimmed, nameValidation: { valid: false, pending: false, error: 'You must choose a name.' } });
      return;
    }
    setState({ name: trimmed, nameValidation: { valid: false, pending: true, error: '' } });
    try {
      const response = await fetch(`${root.dataset.validateNameUrl}?name=${encodeURIComponent(trimmed)}`, {
        headers: { Accept: 'application/json' }
      });
      const data = await response.json();
      setState({
        name: trimmed,
        nameValidation: {
          valid: Boolean(data.valid),
          pending: false,
          error: data.error || ''
        }
      });
    } catch (error) {
      setState({
        name: trimmed,
        nameValidation: {
          valid: false,
          pending: false,
          error: 'Name validation failed. Try again.'
        }
      });
    }
  }

  async function submitCharacter() {
    clearError();
    setState({ submitting: true });
    try {
      const response = await fetch(root.dataset.createUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
          name: state.name,
          race: state.race,
          gender: state.gender,
          body_build: state.body_build,
          skin_tone: state.skin_tone,
          eye_color: state.eye_color,
          hair_color: state.hair_color,
          hair_style: state.hair_style
        })
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'Character creation failed.');
      }
      window.sessionStorage.removeItem(storageKey);
      window.location.assign(root.dataset.dashboardUrl);
    } catch (error) {
      setError(error.message || 'Character creation failed.');
      setState({ submitting: false });
    }
  }

  panel.addEventListener('input', function (event) {
    if (event.target.id !== 'character-builder-name') {
      return;
    }
    clearError();
    const nextName = event.target.value;
    state.name = nextName;
    state.nameValidation = { valid: false, pending: false, error: '' };
    saveState();
    renderButtons();
    window.clearTimeout(nameValidationTimer);
    nameValidationTimer = window.setTimeout(function () {
      validateNameNow(nextName);
    }, 250);
  });

  panel.addEventListener('click', function (event) {
    const button = event.target.closest('[data-choice-field]');
    if (!button) {
      return;
    }
    clearError();
    setState({ [button.dataset.choiceField]: button.dataset.choiceValue });
  });

  backButton.addEventListener('click', function () {
    clearError();
    if (state.currentStep > 0) {
      setState({ currentStep: state.currentStep - 1 });
    }
  });

  nextButton.addEventListener('click', function () {
    clearError();
    if (!validateCurrentStep()) {
      setError('Complete the current step before continuing.');
      return;
    }
    if (state.currentStep === stepKeys.length - 1) {
      submitCharacter();
      return;
    }
    setState({ currentStep: state.currentStep + 1 });
  });

  render();
  if (state.currentStep === 0 && state.name && !state.nameValidation.valid && !state.nameValidation.pending) {
    validateNameNow(state.name);
  }
})();
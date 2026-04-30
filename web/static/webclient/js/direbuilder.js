(function () {
  const page = document.getElementById('direbuilder-page');
  if (!page) {
    return;
  }

  const zoneSelect = document.getElementById('direbuilder-zone-select');
  const tabButtons = Array.from(document.querySelectorAll('[data-direbuilder-tab]'));
  const tabPanels = Array.from(document.querySelectorAll('[data-direbuilder-panel]'));
  const previewSelect = document.getElementById('direbuilder-preview-state');
  const renderedPreview = document.getElementById('direbuilder-rendered-preview');
  const overflowTrigger = document.getElementById('direbuilder-overflow-trigger');
  const overflowMenu = document.getElementById('direbuilder-overflow-menu');
  const toastStack = document.getElementById('direbuilder-toast-stack');
  const modalOverlay = document.getElementById('direbuilder-modal-overlay');
  const modalCard = document.getElementById('direbuilder-modal-card');
  const mapPanel = document.getElementById('builder-map-panel');
  const saveZoneButton = document.getElementById('direbuilder-save-zone');
  const hotLoadButton = document.getElementById('direbuilder-hot-load');
  const discardButton = document.getElementById('direbuilder-discard');
  const generateDescriptionButton = document.getElementById('direbuilder-generate-description');
  const saveErrorBanner = document.getElementById('direbuilder-save-error-banner');
  const saveErrorKicker = document.getElementById('direbuilder-save-error-kicker');
  const saveErrorMessage = document.getElementById('direbuilder-save-error-message');
  const saveErrorDismiss = document.getElementById('direbuilder-save-error-dismiss');
  const zoneScript = document.getElementById('direbuilder-zone-data');
  const zoneContextScript = document.getElementById('direbuilder-zone-context-data');
  const zoneVocabScript = document.getElementById('direbuilder-zone-vocab-data');
  const roomTagVocabScript = document.getElementById('direbuilder-room-tag-vocab-data');
  const tooltipsScript = document.getElementById('direbuilder-tooltips-data');
  const roomTitle = document.getElementById('direbuilder-room-title');
  const roomEnvironment = document.getElementById('direbuilder-room-environment');
  const roomZone = document.getElementById('direbuilder-room-zone');
  const roomEmpty = document.getElementById('direbuilder-room-empty');
  const roomEditorContent = document.getElementById('direbuilder-room-editor-content');
  const identityFields = document.getElementById('direbuilder-identity-fields');
  const manualDescription = document.getElementById('direbuilder-manual-description');
  const descriptionTelemetry = document.getElementById('direbuilder-description-telemetry');
  const tagsList = document.getElementById('direbuilder-tags-list');
  const roomStates = document.getElementById('direbuilder-room-states');
  const statefulDescriptions = document.getElementById('direbuilder-stateful-descriptions');
  const connectionsList = document.getElementById('direbuilder-connections-list');
  const populationNpcs = document.getElementById('direbuilder-population-npcs');
  const populationItems = document.getElementById('direbuilder-population-items');
  const zoneSettingSummary = document.getElementById('direbuilder-zone-setting-summary');
  const zoneSettingBody = document.getElementById('direbuilder-zone-setting-body');
  const zoneEraSummary = document.getElementById('direbuilder-zone-era-summary');
  const zoneEraBody = document.getElementById('direbuilder-zone-era-body');
  const zoneCultureSummary = document.getElementById('direbuilder-zone-culture-summary');
  const zoneCultureBody = document.getElementById('direbuilder-zone-culture-body');
  const zoneMoodSummary = document.getElementById('direbuilder-zone-mood-summary');
  const zoneMoodBody = document.getElementById('direbuilder-zone-mood-body');
  const zoneClimateSummary = document.getElementById('direbuilder-zone-climate-summary');
  const zoneClimateBody = document.getElementById('direbuilder-zone-climate-body');
  const zoneVoiceNotes = document.getElementById('direbuilder-zone-voice-notes');
  const currentZone = zoneScript ? JSON.parse(zoneScript.textContent || 'null') : null;
  const serverZoneContext = zoneContextScript ? JSON.parse(zoneContextScript.textContent || 'null') : null;
  const zoneVocab = zoneVocabScript ? JSON.parse(zoneVocabScript.textContent || '{}') : {};
  const roomTagVocab = roomTagVocabScript ? JSON.parse(roomTagVocabScript.textContent || '{}') : {};
  const tooltips = tooltipsScript ? JSON.parse(tooltipsScript.textContent || '{}') : {};

  const EXIT_DIRECTION_OPTIONS = [
    'north', 'south', 'east', 'west', 'up', 'down', 'northeast', 'northwest', 'southeast', 'southwest',
    'gate', 'arch', 'bridge', 'stair', 'path', 'walk', 'ramp', 'pier', 'ferry', 'dock', 'guild', 'in', 'out',
    'enter', 'leave', 'entry', 'veranda', 'yard',
  ];
  const EXIT_TYPE_OPTIONS = [
    { value: 'typeclasses.exits.Exit', label: 'Exit' },
    { value: 'typeclasses.exits_slow.SlowDireExit', label: 'Slow Dire Exit' },
  ];
  const SAVE_ERROR_MESSAGES = {
    validation_failed: 'Save was rejected. Some fields may be invalid. Please check your edits and try again.',
    zone_not_found: 'This zone no longer exists on disk. Reload the page to recover.',
    write_failed: 'Couldn\'t write to disk. Try again, or check the server logs.',
    internal_error: 'Save failed unexpectedly. Try again. If this persists, check the server logs.',
    network_error: 'Save failed unexpectedly. Try again. If this persists, check the server logs.',
    operation_in_progress: 'Another save, discard, or hot load is still running. Wait for it to finish, then try again.',
  };
  const DISCARD_ERROR_MESSAGES = {
    zone_not_found: 'This zone no longer exists on disk. Reload the page to recover.',
    internal_error: 'Couldn\'t reload this zone from disk. Try again. If this persists, check the server logs.',
    network_error: 'Couldn\'t reload this zone from disk. Check your connection and try again.',
    operation_in_progress: 'Another save, discard, or hot load is still running. Wait for it to finish, then try again.',
  };
  const HOT_LOAD_ERROR_MESSAGES = {
    validation_failed: 'Zone YAML is invalid. Fix the zone file on disk and try again.',
    zone_not_found: 'This zone no longer exists on disk. Reload the page to recover.',
    runtime_error: 'Hot load failed mid-operation. Live game state may be partially updated. Consider reloading the running server if behavior becomes unexpected.',
    internal_error: 'Hot load failed unexpectedly. Try again. If this persists, check the server logs.',
    network_error: 'Couldn\'t reach the server. Check your connection and try again.',
    operation_in_progress: 'Another save, discard, or hot load is still running. Wait for it to finish, then try again.',
  };
  let tooltipHideTimeout = null;
  let activeTooltipButton = null;
  const tooltipPopover = document.createElement('div');
  tooltipPopover.id = 'direbuilder-tooltip-popover';
  tooltipPopover.className = 'direbuilder-tooltip-popover';
  tooltipPopover.setAttribute('role', 'tooltip');
  tooltipPopover.setAttribute('tabindex', '-1');
  tooltipPopover.hidden = true;
  document.body.appendChild(tooltipPopover);

  function clearTooltipHideTimer() {
    if (tooltipHideTimeout) {
      window.clearTimeout(tooltipHideTimeout);
      tooltipHideTimeout = null;
    }
  }

  function scheduleTooltipHide() {
    clearTooltipHideTimer();
    tooltipHideTimeout = window.setTimeout(() => {
      hideTooltipPopover();
    }, 200);
  }

  function hideTooltipPopover(options = {}) {
    clearTooltipHideTimer();
    if (activeTooltipButton) {
      activeTooltipButton.setAttribute('aria-expanded', 'false');
      activeTooltipButton.removeAttribute('aria-describedby');
      if (options.returnFocus) {
        activeTooltipButton.focus();
      }
    }
    activeTooltipButton = null;
    tooltipPopover.hidden = true;
    tooltipPopover.innerHTML = '';
  }

  function positionTooltipPopover(button) {
    const rect = button.getBoundingClientRect();
    const popoverRect = tooltipPopover.getBoundingClientRect();
    let left = rect.right + 12;
    let top = rect.top;

    if (left + popoverRect.width > window.innerWidth - 16) {
      left = Math.min(rect.left, window.innerWidth - popoverRect.width - 16);
      top = rect.bottom + 10;
    }
    if (top + popoverRect.height > window.innerHeight - 16) {
      top = Math.max(16, rect.top - popoverRect.height - 10);
    }

    tooltipPopover.style.left = `${Math.max(16, left)}px`;
    tooltipPopover.style.top = `${Math.max(16, top)}px`;
  }

  function showTooltipPopover(button, fieldPath) {
    const entry = tooltips?.[fieldPath];
    if (!entry) {
      return;
    }
    clearTooltipHideTimer();
    if (activeTooltipButton && activeTooltipButton !== button) {
      activeTooltipButton.setAttribute('aria-expanded', 'false');
      activeTooltipButton.removeAttribute('aria-describedby');
    }
    tooltipPopover.innerHTML = `
      <div class="direbuilder-tooltip-purpose">${escapeHtml(entry.purpose || '')}</div>
      ${Array.isArray(entry.examples) && entry.examples.length ? `<div class="direbuilder-tooltip-examples"><span class="direbuilder-tooltip-label">Examples:</span> ${escapeHtml(entry.examples.join(', '))}</div>` : ''}
      ${entry.ai_note ? `<div class="direbuilder-tooltip-ai-note"><span class="direbuilder-tooltip-label">AI:</span> ${escapeHtml(entry.ai_note)}</div>` : ''}
    `;
    tooltipPopover.hidden = false;
    activeTooltipButton = button;
    button.setAttribute('aria-expanded', 'true');
    button.setAttribute('aria-describedby', tooltipPopover.id);
    positionTooltipPopover(button);
  }

  function attachTooltipIcon(labelElement, fieldPath) {
    if (!labelElement || !fieldPath || !tooltips?.[fieldPath]) {
      return;
    }
    if (labelElement.querySelector('.direbuilder-tooltip-icon')) {
      return;
    }
    const labelText = String(labelElement.textContent || '').trim() || 'field';
    labelElement.classList.add('direbuilder-tooltip-anchor');
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'direbuilder-tooltip-icon';
    button.setAttribute('aria-haspopup', 'true');
    button.setAttribute('aria-expanded', 'false');
    button.setAttribute('aria-label', `More information about ${labelText}`);
    button.textContent = 'ⓘ';
    button.addEventListener('mouseenter', () => showTooltipPopover(button, fieldPath));
    button.addEventListener('mouseleave', scheduleTooltipHide);
    button.addEventListener('focus', () => showTooltipPopover(button, fieldPath));
    button.addEventListener('blur', scheduleTooltipHide);
    button.addEventListener('click', (event) => {
      event.preventDefault();
      event.stopPropagation();
      if (activeTooltipButton === button && !tooltipPopover.hidden) {
        hideTooltipPopover();
        return;
      }
      showTooltipPopover(button, fieldPath);
    });
    button.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        hideTooltipPopover({ returnFocus: true });
      }
    });
    labelElement.appendChild(button);
  }

  function attachTooltipIconsIn(root) {
    if (!root) {
      return;
    }
    root.querySelectorAll('[data-tooltip-field]').forEach((labelElement) => {
      attachTooltipIcon(labelElement, labelElement.dataset.tooltipField);
    });
  }

  tooltipPopover.addEventListener('mouseenter', clearTooltipHideTimer);
  tooltipPopover.addEventListener('mouseleave', scheduleTooltipHide);
  tooltipPopover.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      event.preventDefault();
      hideTooltipPopover({ returnFocus: true });
    }
  });
  document.addEventListener('click', (event) => {
    if (tooltipPopover.hidden) {
      return;
    }
    if (tooltipPopover.contains(event.target) || activeTooltipButton?.contains(event.target)) {
      return;
    }
    hideTooltipPopover();
  });
  window.addEventListener('resize', () => {
    if (activeTooltipButton && !tooltipPopover.hidden) {
      positionTooltipPopover(activeTooltipButton);
    }
  });
  document.addEventListener('scroll', () => {
    if (activeTooltipButton && !tooltipPopover.hidden) {
      positionTooltipPopover(activeTooltipButton);
    }
  }, true);

  function cloneData(value) {
    return value == null ? value : JSON.parse(JSON.stringify(value));
  }

  function deepFreeze(value) {
    if (!value || typeof value !== 'object' || Object.isFrozen(value)) {
      return value;
    }
    Object.freeze(value);
    Object.keys(value).forEach((key) => deepFreeze(value[key]));
    return value;
  }

  function ensureArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function ensureObject(value) {
    return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
  }

  function normalizePopulationStorageChoice(value) {
    const choice = String(value || '').trim().toLowerCase();
    return choice === 'placements' || choice === 'rooms' ? choice : 'unknown';
  }

  function cleanFallbackText(value) {
    const text = String(value || '').trim();
    return text === '(not set)' ? '' : text;
  }

  function cleanFallbackList(value) {
    return normalizeList(value).filter((entry) => entry !== '(not set)');
  }

  function normalizeWorkingZone(zone, fallbackContext) {
    if (!zone) {
      return zone;
    }
    const normalized = cloneData(zone);
    normalized.generation_context = ensureObject(normalized.generation_context);
    normalized.generation_context.setting_type = String(normalized.generation_context.setting_type || cleanFallbackText(fallbackContext?.setting_type) || '').trim();
    normalized.generation_context.era_feel = String(normalized.generation_context.era_feel || cleanFallbackText(fallbackContext?.era_feel) || '').trim();
    normalized.generation_context.culture = normalizeList(normalized.generation_context.culture || cleanFallbackList(fallbackContext?.culture) || []);
    normalized.generation_context.mood = normalizeList(normalized.generation_context.mood || cleanFallbackList(fallbackContext?.mood) || []);
    normalized.generation_context.climate = String(normalized.generation_context.climate || cleanFallbackText(fallbackContext?.climate) || '').trim();
    normalized.generation_context.voice = String(normalized.generation_context.voice || cleanFallbackText(fallbackContext?.voice) || '').trim();
    normalized.placements = ensureObject(normalized.placements);
    normalized.placements.npcs = ensureArray(normalized.placements.npcs);
    normalized.placements.items = ensureArray(normalized.placements.items);
    normalized._direbuilder = ensureObject(normalized._direbuilder);
    normalized._direbuilder.population_storage = ensureObject(normalized._direbuilder.population_storage);
    normalized._direbuilder.population_storage.npcs = normalizePopulationStorageChoice(normalized._direbuilder.population_storage.npcs);
    normalized._direbuilder.population_storage.items = normalizePopulationStorageChoice(normalized._direbuilder.population_storage.items);
    normalized.rooms = ensureArray(normalized.rooms).map((room) => {
      const nextRoom = ensureObject(room);
      nextRoom.short_desc = String(nextRoom.short_desc || '');
      nextRoom.desc = String(nextRoom.desc || '');
      nextRoom.environment = String(nextRoom.environment || 'city').trim().toLowerCase();
      nextRoom.tags = ensureObject(nextRoom.tags);
      nextRoom.tags.custom = normalizeList(nextRoom.tags.custom);
      nextRoom.tags.atmosphere = ensureObject(nextRoom.tags.atmosphere);
      nextRoom.tags.atmosphere.materials = normalizeList(nextRoom.tags.atmosphere.materials);
      nextRoom.tags.atmosphere.social_character = normalizeList(nextRoom.tags.atmosphere.social_character);
      nextRoom.tags.atmosphere.surroundings = normalizeList(nextRoom.tags.atmosphere.surroundings);
      nextRoom.tags.atmosphere.sensory = normalizeList(nextRoom.tags.atmosphere.sensory);
      nextRoom.room_states = normalizeList(nextRoom.room_states);
      nextRoom.stateful_descs = ensureObject(nextRoom.stateful_descs);
      nextRoom.details = ensureObject(nextRoom.details);
      nextRoom.ambient = ensureObject(nextRoom.ambient);
      nextRoom.ambient.rate = Number(nextRoom.ambient.rate || 0) || 0;
      nextRoom.ambient.messages = normalizeList(nextRoom.ambient.messages);
      nextRoom.exits = ensureObject(nextRoom.exits);
      nextRoom.npcs = normalizeList(nextRoom.npcs);
      nextRoom.items = ensureArray(nextRoom.items);
      return nextRoom;
    });
    return normalized;
  }

  let originalZone = deepFreeze(normalizeWorkingZone(currentZone, serverZoneContext));
  let workingZone = normalizeWorkingZone(currentZone, serverZoneContext);
  const state = {
    currentRoomId: String(workingZone?.rooms?.[0]?.id || ''),
    previewMode: String(previewSelect?.value || 'default'),
    activeTabId: String(tabButtons.find((button) => button.classList.contains('is-active'))?.dataset.direbuilderTab || 'identity'),
    saveState: 'idle',
    lastSaveError: null,
    savePromise: null,
    discardState: 'idle',
    lastDiscardError: null,
    discardPromise: null,
    hotLoadState: 'idle',
    lastHotLoadError: null,
    lastHotLoadSummary: null,
    hotLoadPromise: null,
    generationState: 'idle',
    generationPromise: null,
    generationRoomId: null,
    lastGenerationTelemetryByRoom: {},
  };

  function getRoomsById() {
    return new Map((workingZone?.rooms || []).map((room) => [String(room.id || ''), room]));
  }

  function getCurrentRoom(roomId = state.currentRoomId) {
    return roomId ? getRoomsById().get(String(roomId)) || null : null;
  }

  function computeZoneDiff(original, working) {
    return JSON.stringify(original) === JSON.stringify(working) ? null : { changed: true };
  }

  function isDirty() {
    return computeZoneDiff(originalZone, workingZone) !== null;
  }

  function isSaving() {
    return state.saveState === 'saving';
  }

  function isDiscarding() {
    return state.discardState === 'discarding';
  }

  function isHotLoading() {
    return state.hotLoadState === 'hot_loading';
  }

  function isGeneratingDescription() {
    return state.generationState === 'generating';
  }

  function isOperationInProgress() {
    return isSaving() || isDiscarding() || isHotLoading();
  }

  function getPopulationStorage(kind, zone = workingZone) {
    return normalizePopulationStorageChoice(zone?._direbuilder?.population_storage?.[kind]);
  }

  function getEditableControls() {
    return Array.from(page.querySelectorAll('button, input, select, textarea')).filter((element) => {
      if (!element || modalOverlay?.contains(element)) {
        return false;
      }
      return (
        element === zoneSelect
        || element.closest('.direbuilder-zone-panel')
        || element.closest('.direbuilder-room-panel')
      );
    });
  }

  function setEditableLockState(locked) {
    page.classList.toggle('is-ui-locked', locked);
    getEditableControls().forEach((element) => {
      element.disabled = locked;
    });
  }

  function applySaveUiState() {
    setEditableLockState(isOperationInProgress());
    updateDirtyIndicator();
  }

  function updateDirtyIndicator() {
    if (!saveZoneButton) {
      return;
    }
    const dirty = isDirty();
    const saving = isSaving();
    const hotLoading = isHotLoading();
    saveZoneButton.classList.toggle('is-dirty', dirty);
    saveZoneButton.classList.toggle('is-saving', saving);
    saveZoneButton.textContent = saving ? 'Saving...' : dirty ? 'Save Zone*' : 'Save Zone';
    saveZoneButton.disabled = isOperationInProgress();
    if (hotLoadButton) {
      hotLoadButton.classList.toggle('is-hot-loading', hotLoading);
      hotLoadButton.textContent = hotLoading ? 'Hot Loading...' : 'Hot Load';
      hotLoadButton.disabled = isOperationInProgress();
    }
    if (discardButton) {
      discardButton.disabled = isOperationInProgress() || !dirty;
    }
    zoneSelect?.closest('.direbuilder-zone-switcher')?.classList.toggle('is-dirty', dirty);
    zoneSelect?.closest('.direbuilder-zone-switcher')?.classList.toggle('is-locked', isOperationInProgress());
  }

  function getGenerationContext() {
    workingZone.generation_context = ensureObject(workingZone.generation_context);
    return workingZone.generation_context;
  }

  function getCurrentRoomPlacements(kind, roomId) {
    if (getPopulationStorage(kind) === 'placements') {
      const zonePlacements = ensureArray(workingZone?.placements?.[kind]);
      return zonePlacements.filter((entry) => String(entry?.room || '') === String(roomId || ''));
    }
    if (kind === 'npcs' && ensureArray(workingZone?.placements?.npcs).length && getPopulationStorage(kind) === 'unknown') {
      return workingZone.placements.npcs.filter((entry) => String(entry?.room || '') === String(roomId || ''));
    }
    if (kind === 'items' && ensureArray(workingZone?.placements?.items).length && getPopulationStorage(kind) === 'unknown') {
      return workingZone.placements.items.filter((entry) => String(entry?.room || '') === String(roomId || ''));
    }
    const room = getCurrentRoom(roomId);
    if (!room) {
      return [];
    }
    if (kind === 'npcs') {
      return normalizeList(room.npcs).map((npcId) => ({ id: npcId, room: room.id, typeclass: '', prototype: null }));
    }
    return ensureArray(room.items).map((entry) => ({ ...entry, room: room.id }));
  }

  function setCurrentRoomPlacements(kind, roomId, entries) {
    if (!roomId) {
      return;
    }
    if (getPopulationStorage(kind) === 'placements') {
      workingZone.placements[kind] = ensureArray(workingZone?.placements?.[kind])
        .filter((entry) => String(entry?.room || '') !== String(roomId))
        .concat(entries.map((entry) => ({ ...entry, room: roomId })));
      return;
    }
    if (kind === 'npcs' && ensureArray(workingZone?.placements?.npcs).length && getPopulationStorage(kind) === 'unknown') {
      workingZone.placements.npcs = workingZone.placements.npcs
        .filter((entry) => String(entry?.room || '') !== String(roomId))
        .concat(entries.map((entry) => ({ ...entry, room: roomId })));
      return;
    }
    if (kind === 'items' && ensureArray(workingZone?.placements?.items).length && getPopulationStorage(kind) === 'unknown') {
      workingZone.placements.items = workingZone.placements.items
        .filter((entry) => String(entry?.room || '') !== String(roomId))
        .concat(entries.map((entry) => ({ ...entry, room: roomId })));
      return;
    }
    const room = getCurrentRoom(roomId);
    if (!room) {
      return;
    }
    if (kind === 'npcs') {
      room.npcs = entries.map((entry) => String(entry?.id || '').trim()).filter(Boolean);
      return;
    }
    room.items = entries.map((entry) => ({
      id: String(entry?.id || '').trim(),
      count: Number(entry?.count || 1) || 1,
      typeclass: String(entry?.typeclass || '').trim(),
      prototype: entry?.prototype ?? null,
    })).filter((entry) => entry.id);
  }

  function summarizeValues(values, emptyValue = '(not set)') {
    const normalized = normalizeList(values);
    return normalized.length ? normalized.map(titleize).join(', ') : emptyValue;
  }

  function makeOptionMarkup(options, selectedValue) {
    return options.map((option) => {
      const value = typeof option === 'string' ? option : option.value;
      const label = typeof option === 'string' ? titleize(option) : option.label;
      const selected = String(selectedValue || '') === String(value) ? ' selected' : '';
      return `<option value="${escapeHtml(value)}"${selected}>${escapeHtml(label)}</option>`;
    }).join('');
  }

  function renderChipEditor(target, options) {
    if (!target) {
      return;
    }
    const values = normalizeList(options.values);
    const availableOptions = normalizeList(options.availableOptions);
    if (availableOptions.length) {
      const availableOptionMap = new Map(availableOptions.map((value) => [String(value || '').trim().toLowerCase(), value]));
      const customValues = values.filter((value) => !availableOptionMap.has(String(value || '').trim().toLowerCase()));
      target.innerHTML = `
        ${options.note ? `<p class="direbuilder-note">${escapeHtml(options.note)}</p>` : ''}
        <div class="direbuilder-pill-row direbuilder-edit-pill-row">
          ${availableOptions.map((value) => {
            const selected = values.includes(value);
            return `<button type="button" class="direbuilder-pill direbuilder-pill-button${selected ? ' is-selected' : ''}" data-chip-toggle="${escapeHtml(value)}" aria-pressed="${selected ? 'true' : 'false'}">${escapeHtml(titleize(value))}</button>`;
          }).join('')}
          ${customValues.map((value) => `<button type="button" class="direbuilder-pill direbuilder-pill-button direbuilder-pill-custom is-selected" data-chip-toggle="${escapeHtml(value)}" aria-pressed="true" title="Custom - added in this zone" aria-label="Custom value ${escapeHtml(titleize(value))}"><span class="direbuilder-pill-custom-marker">~</span>${escapeHtml(titleize(value))}</button>`).join('')}
        </div>
        ${options.allowCustomInput ? `<div class="direbuilder-inline-editor direbuilder-custom-chip-row"><input class="direbuilder-compact-input direbuilder-custom-chip-input" type="text" value="" placeholder="${escapeHtml(options.customPlaceholder || 'Add custom...')}" data-chip-custom-input><button class="direbuilder-button direbuilder-button-secondary direbuilder-mini-button direbuilder-custom-chip-add" type="button" data-chip-custom-add>+ Add</button></div>` : ''}
      `;

      target.querySelectorAll('[data-chip-toggle]').forEach((button) => {
        button.addEventListener('click', function () {
          const value = String(button.dataset.chipToggle || '').trim();
          if (!value) {
            return;
          }
          const nextValues = options.allowMultiple === false
            ? (values.includes(value) ? [] : [value])
            : (values.includes(value) ? values.filter((entry) => entry !== value) : values.concat(value));
          options.onChange(nextValues);
        });
      });
      const customInput = target.querySelector('[data-chip-custom-input]');
      function submitCustomValue() {
        const rawValue = String(customInput?.value || '').trim();
        if (!rawValue) {
          return;
        }
        const canonicalMatch = availableOptionMap.get(rawValue.toLowerCase());
        const nextValue = canonicalMatch || slugifyTagValue(rawValue);
        if (!nextValue) {
          return;
        }
        const nextValues = options.allowMultiple === false
          ? (values.includes(nextValue) ? [] : [nextValue])
          : (values.includes(nextValue) ? values : values.concat(nextValue).filter((entry, index, array) => array.findIndex((candidate) => candidate.toLowerCase() === entry.toLowerCase()) === index));
        if (customInput) {
          customInput.value = '';
        }
        options.onChange(nextValues);
      }
      target.querySelector('[data-chip-custom-add]')?.addEventListener('click', submitCustomValue);
      customInput?.addEventListener('keydown', function (event) {
        if (event.key === 'Enter') {
          event.preventDefault();
          submitCustomValue();
        }
      });
      return;
    }
    target.innerHTML = `
      ${options.note ? `<p class="direbuilder-note">${escapeHtml(options.note)}</p>` : ''}
      <div class="direbuilder-pill-row direbuilder-edit-pill-row">
        ${values.length ? values.map((value) => `<button type="button" class="direbuilder-pill direbuilder-pill-button" data-chip-remove="${escapeHtml(value)}">${escapeHtml(titleize(value))}<span class="direbuilder-pill-remove">x</span></button>`).join('') : '<span class="direbuilder-note">No values set.</span>'}
      </div>
      <div class="direbuilder-inline-editor">
        <input class="direbuilder-compact-input" type="text" value="" placeholder="${escapeHtml(options.placeholder || 'Add value')}" data-chip-input>
        <button class="direbuilder-button direbuilder-button-secondary direbuilder-mini-button" type="button" data-chip-add>${escapeHtml(options.buttonLabel || 'Add')}</button>
      </div>
    `;

    target.querySelectorAll('[data-chip-remove]').forEach((button) => {
      button.addEventListener('click', function () {
        options.onChange(values.filter((value) => value !== button.dataset.chipRemove));
      });
    });
    const input = target.querySelector('[data-chip-input]');
    target.querySelector('[data-chip-add]')?.addEventListener('click', function () {
      const value = String(input?.value || '').trim();
      if (!value) {
        return;
      }
      const nextValues = options.allowMultiple === false ? [value] : values.concat(value).filter((entry, index, array) => array.indexOf(entry) === index);
      options.onChange(nextValues);
    });
  }

  function renderZoneEditor() {
    const generationContext = getGenerationContext();
    if (zoneSettingSummary) {
      zoneSettingSummary.textContent = summarizeValues(generationContext.setting_type);
    }
    renderChipEditor(zoneSettingBody, {
      values: generationContext.setting_type,
      availableOptions: getZoneVocabOptions('setting_types'),
      allowMultiple: false,
      note: 'Current scaffold value for zone-level generation context.',
      onChange(nextValues) {
        generationContext.setting_type = nextValues[0] || '';
        renderZoneEditor();
        updateDirtyIndicator();
      },
    });

    if (zoneEraSummary) {
      zoneEraSummary.textContent = summarizeValues(generationContext.era_feel);
    }
    renderChipEditor(zoneEraBody, {
      values: generationContext.era_feel,
      availableOptions: getZoneVocabOptions('eras'),
      allowMultiple: false,
      note: 'Current era guidance loaded from the zone YAML.',
      onChange(nextValues) {
        generationContext.era_feel = nextValues[0] || '';
        renderZoneEditor();
        updateDirtyIndicator();
      },
    });

    if (zoneCultureSummary) {
      zoneCultureSummary.textContent = summarizeValues(generationContext.culture);
    }
    renderChipEditor(zoneCultureBody, {
      values: generationContext.culture,
      availableOptions: getZoneVocabOptions('cultures'),
      allowMultiple: true,
      onChange(nextValues) {
        generationContext.culture = nextValues;
        renderZoneEditor();
        updateDirtyIndicator();
      },
    });

    if (zoneMoodSummary) {
      zoneMoodSummary.textContent = summarizeValues(generationContext.mood);
    }
    renderChipEditor(zoneMoodBody, {
      values: generationContext.mood,
      availableOptions: getZoneVocabOptions('moods'),
      allowMultiple: true,
      onChange(nextValues) {
        generationContext.mood = nextValues;
        renderZoneEditor();
        updateDirtyIndicator();
      },
    });

    if (zoneClimateSummary) {
      zoneClimateSummary.textContent = summarizeValues(generationContext.climate);
    }
    renderChipEditor(zoneClimateBody, {
      values: generationContext.climate,
      availableOptions: getZoneVocabOptions('climates'),
      allowMultiple: false,
      note: 'Climate informs the room description pipeline in later phases.',
      onChange(nextValues) {
        generationContext.climate = nextValues[0] || '';
        renderZoneEditor();
        updateDirtyIndicator();
      },
    });

    if (zoneVoiceNotes) {
      zoneVoiceNotes.value = generationContext.voice || '';
    }
    attachTooltipIconsIn(page);
  }

  function buildGenerateDescriptionUrl(zoneId, roomId) {
    return `/direbuilder/api/zone/${encodeURIComponent(zoneId)}/room/${encodeURIComponent(roomId)}/generate-description/`;
  }

  function formatGenerationTelemetry(telemetry) {
    if (!telemetry) {
      return 'No generation run yet.';
    }
    const cost = Number(telemetry.approximate_cost_usd || 0);
    const elapsedSeconds = Number(telemetry.elapsed_ms || 0) / 1000;
    return `Last generation: $${cost.toFixed(3)} · ${elapsedSeconds.toFixed(1)}s`;
  }

  function updateDescriptionGenerationUi(room = getCurrentRoom()) {
    const hasDescription = Boolean(String(room?.desc || '').trim());
    if (generateDescriptionButton) {
      if (isGeneratingDescription()) {
        generateDescriptionButton.innerHTML = '<span class="direbuilder-button-spinner" aria-hidden="true"></span>Generating...';
      } else {
        generateDescriptionButton.textContent = hasDescription ? 'Regenerate' : 'Generate Description';
      }
      generateDescriptionButton.disabled = !room || isGeneratingDescription();
    }
    if (descriptionTelemetry) {
      const roomId = String(room?.id || '');
      descriptionTelemetry.textContent = formatGenerationTelemetry(state.lastGenerationTelemetryByRoom[roomId] || null);
    }
    mapPanel?.classList.toggle('is-generation-locked', isGeneratingDescription());
  }

  function buildSaveUrl(zoneId) {
    return `/direbuilder/api/zone/${encodeURIComponent(zoneId)}/save/`;
  }

  function buildZoneDetailUrl(zoneId) {
    return `/direbuilder/api/zone/${encodeURIComponent(zoneId)}/`;
  }

  function buildHotLoadUrl(zoneId) {
    return `/direbuilder/api/zone/${encodeURIComponent(zoneId)}/hot-load/`;
  }

  function getSaveFailureMessage(code) {
    return SAVE_ERROR_MESSAGES[code] || SAVE_ERROR_MESSAGES.internal_error;
  }

  function getDiscardFailureMessage(code) {
    return DISCARD_ERROR_MESSAGES[code] || DISCARD_ERROR_MESSAGES.internal_error;
  }

  function getHotLoadFailureMessage(code) {
    return HOT_LOAD_ERROR_MESSAGES[code] || HOT_LOAD_ERROR_MESSAGES.internal_error;
  }

  function clearSaveErrorBanner() {
    if (!saveErrorBanner || !saveErrorMessage) {
      return;
    }
    saveErrorBanner.hidden = true;
    if (saveErrorKicker) {
      saveErrorKicker.textContent = 'Save Error';
    }
    saveErrorMessage.textContent = '';
  }

  function getGenerationFailureMessage(payload, fallbackCode = 'internal_error') {
    const code = String(payload?.error || '').trim() || fallbackCode;
    const baseMessage = String(payload?.message || '').trim() || 'Description generation failed unexpectedly. Try again. If this persists, check the server logs.';
    if (payload?.retriable) {
      return `${baseMessage} Retry is safe.`;
    }
    return baseMessage;
  }

  function showSaveErrorBanner(message, kicker = 'Save Error') {
    if (!saveErrorBanner || !saveErrorMessage) {
      return;
    }
    if (saveErrorKicker) {
      saveErrorKicker.textContent = kicker;
    }
    saveErrorMessage.textContent = message;
    saveErrorBanner.hidden = false;
  }

  async function readJsonSafely(response) {
    try {
      return await response.json();
    } catch (error) {
      return null;
    }
  }

  async function parseSaveFailure(response) {
    const payload = await readJsonSafely(response);
    const code = String(payload?.error || '').trim() || (response.status === 409 ? 'operation_in_progress' : response.status === 404 ? 'zone_not_found' : response.status === 400 ? 'validation_failed' : 'internal_error');
    return {
      code,
      message: String(payload?.message || '').trim() || getSaveFailureMessage(code),
    };
  }

  async function parseDiscardFailure(response) {
    const payload = await readJsonSafely(response);
    const code = String(payload?.error || '').trim() || (response.status === 409 ? 'operation_in_progress' : response.status === 404 ? 'zone_not_found' : 'internal_error');
    return {
      code,
      message: String(payload?.message || '').trim() || getDiscardFailureMessage(code),
    };
  }

  async function parseHotLoadFailure(response) {
    const payload = await readJsonSafely(response);
    const code = String(payload?.error || '').trim() || (
      response.status === 409 ? 'operation_in_progress'
        : response.status === 404 ? 'zone_not_found'
          : response.status === 400 ? 'validation_failed'
            : 'internal_error'
    );
    return {
      code,
      message: String(payload?.message || '').trim() || getHotLoadFailureMessage(code),
    };
  }

  async function parseGenerationFailure(response) {
    const payload = await readJsonSafely(response);
    return {
      code: String(payload?.error || '').trim() || (response.status === 400 ? 'validation_failed' : 'internal_error'),
      message: getGenerationFailureMessage(payload, response.status === 400 ? 'validation_failed' : 'internal_error'),
      retriable: Boolean(payload?.retriable),
    };
  }

  function fetchWithTimeout(url, options, timeoutMs = 15000) {
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);
    return window.fetch(url, { ...options, signal: controller.signal }).finally(() => {
      window.clearTimeout(timeoutId);
    });
  }

  function syncCanonicalZone(savedZone) {
    const canonicalZone = normalizeWorkingZone(savedZone, null);
    originalZone = deepFreeze(cloneData(canonicalZone));
    workingZone = normalizeWorkingZone(canonicalZone, null);
    page.dataset.currentZoneId = String(workingZone?.zone_id || '');
    const roomExists = (workingZone?.rooms || []).some((room) => String(room?.id || '') === String(state.currentRoomId || ''));
    state.currentRoomId = roomExists ? String(state.currentRoomId || '') : String(workingZone?.rooms?.[0]?.id || '');
    setTab(state.activeTabId || 'identity');
    renderZoneEditor();
    renderRoomEditor(state.currentRoomId || null);
    mountMap();
    updateDirtyIndicator();
    return canonicalZone;
  }

  function createSaveError(code, message) {
    const error = new Error(message);
    error.code = code;
    return error;
  }

  function createDiscardError(code, message) {
    const error = new Error(message);
    error.code = code;
    return error;
  }

  function createHotLoadError(code, message) {
    const error = new Error(message);
    error.code = code;
    return error;
  }

  function formatHotLoadSummary(summary) {
    const warnings = ensureArray(summary?.warnings).filter(Boolean);
    const lines = [
      'Hot load complete.',
      `- ${Number(summary?.rooms_updated || 0)} rooms updated`,
      `- ${Number(summary?.rooms_created || 0)} rooms created`,
      `- ${Number(summary?.rooms_preserved_stale || 0)} rooms preserved as stale`,
      `- ${Number(summary?.npcs_respawned || 0)} NPCs respawned`,
      `- ${Number(summary?.items_respawned || 0)} items respawned`,
    ];
    warnings.forEach((warning) => {
      lines.push(`- Warning: ${warning}`);
    });
    return lines.join('\n');
  }

  function saveWorkingZone(options = {}) {
    if (!workingZone?.zone_id) {
      return Promise.reject(createSaveError('validation_failed', getSaveFailureMessage('validation_failed')));
    }
    if (isHotLoading() && !options.allowDuringHotLoad) {
      return Promise.reject(createSaveError('operation_in_progress', getSaveFailureMessage('operation_in_progress')));
    }
    if (isDiscarding()) {
      return Promise.reject(createSaveError('operation_in_progress', getSaveFailureMessage('operation_in_progress')));
    }
    if (state.savePromise) {
      return state.savePromise;
    }

    state.saveState = 'saving';
    state.lastSaveError = null;
    applySaveUiState();

    const zoneId = String(workingZone.zone_id || '').trim();
    const payload = cloneData(workingZone);
    state.savePromise = fetchWithTimeout(buildSaveUrl(zoneId), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    }).then(async (response) => {
      if (!response.ok) {
        const failure = await parseSaveFailure(response);
        throw createSaveError(failure.code, failure.message);
      }
      const savedZone = await response.json();
      state.saveState = 'succeeded';
      state.lastSaveError = null;
      clearSaveErrorBanner();
      const canonicalZone = syncCanonicalZone(savedZone);
      if (!options.silentSuccessToast) {
        showToast('Zone saved.');
      }
      return canonicalZone;
    }).catch((error) => {
      const code = error?.name === 'AbortError' ? 'network_error' : String(error?.code || 'network_error');
      const message = String(error?.message || getSaveFailureMessage(code));
      state.saveState = 'failed';
      state.lastSaveError = code;
      updateDirtyIndicator();
      showSaveErrorBanner(message);
      if (!options.silentFailureToast) {
        showToast(message);
      }
      throw createSaveError(code, message);
    }).finally(() => {
      state.savePromise = null;
      applySaveUiState();
    });

    return state.savePromise;
  }

  function discardWorkingZone(options = {}) {
    const zoneId = String(workingZone?.zone_id || page.dataset.currentZoneId || '').trim();
    if (!zoneId) {
      return Promise.reject(createDiscardError('zone_not_found', getDiscardFailureMessage('zone_not_found')));
    }
    if (isHotLoading()) {
      return Promise.reject(createDiscardError('operation_in_progress', getDiscardFailureMessage('operation_in_progress')));
    }
    if (isSaving()) {
      return Promise.reject(createDiscardError('operation_in_progress', getDiscardFailureMessage('operation_in_progress')));
    }
    if (state.discardPromise) {
      return state.discardPromise;
    }

    state.discardState = 'discarding';
    state.lastDiscardError = null;
    applySaveUiState();

    state.discardPromise = fetchWithTimeout(buildZoneDetailUrl(zoneId), {
      method: 'GET',
      headers: {
        Accept: 'application/json',
      },
    }).then(async (response) => {
      if (!response.ok) {
        const failure = await parseDiscardFailure(response);
        throw createDiscardError(failure.code, failure.message);
      }
      const canonicalZone = syncCanonicalZone(await response.json());
      state.saveState = 'idle';
      state.lastSaveError = null;
      state.discardState = 'succeeded';
      state.lastDiscardError = null;
      if (!options.silentSuccessToast) {
        showToast('Unsaved changes discarded.');
      }
      return canonicalZone;
    }).catch((error) => {
      const code = error?.name === 'AbortError' ? 'network_error' : String(error?.code || 'network_error');
      const message = String(error?.message || getDiscardFailureMessage(code));
      state.discardState = 'failed';
      state.lastDiscardError = code;
      if (!options.silentFailureToast) {
        showToast(message);
      }
      throw createDiscardError(code, message);
    }).finally(() => {
      state.discardPromise = null;
      applySaveUiState();
    });

    return state.discardPromise;
  }

  function hotLoadCurrentZone(options = {}) {
    const zoneId = String(workingZone?.zone_id || page.dataset.currentZoneId || '').trim();
    if (!zoneId) {
      return Promise.reject(createHotLoadError('zone_not_found', getHotLoadFailureMessage('zone_not_found')));
    }
    if (isSaving() || isDiscarding()) {
      return Promise.reject(createHotLoadError('operation_in_progress', getHotLoadFailureMessage('operation_in_progress')));
    }
    if (state.hotLoadPromise) {
      return state.hotLoadPromise;
    }

    state.hotLoadState = 'hot_loading';
    state.lastHotLoadError = null;
    applySaveUiState();

    state.hotLoadPromise = Promise.resolve().then(async () => {
      if (isDirty()) {
        try {
          await saveWorkingZone({
            silentSuccessToast: true,
            allowDuringHotLoad: true,
          });
        } catch (error) {
          error.hotLoadSaveFailure = true;
          throw error;
        }
      }

      const response = await window.fetch(buildHotLoadUrl(zoneId), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({}),
      });

      if (!response.ok) {
        const failure = await parseHotLoadFailure(response);
        throw createHotLoadError(failure.code, failure.message);
      }

      const payload = await response.json();
      const summary = cloneData(ensureObject(payload?.summary));
      state.hotLoadState = 'succeeded';
      state.lastHotLoadError = null;
      state.lastHotLoadSummary = summary;
      if (!options.silentSuccessToast) {
        showToast(formatHotLoadSummary(summary));
      }
      return summary;
    }).catch((error) => {
      if (error?.hotLoadSaveFailure) {
        state.hotLoadState = 'failed';
        state.lastHotLoadError = String(error?.code || 'save_failed');
        throw error;
      }
      const code = error?.name === 'AbortError' ? 'network_error' : String(error?.code || 'network_error');
      const message = String(error?.message || getHotLoadFailureMessage(code));
      state.hotLoadState = 'failed';
      state.lastHotLoadError = code;
      if (!options.silentFailureToast) {
        showToast(message);
      }
      throw createHotLoadError(code, message);
    }).finally(() => {
      state.hotLoadPromise = null;
      applySaveUiState();
    });

    return state.hotLoadPromise;
  }

  function setTab(targetId) {
    state.activeTabId = targetId;
    tabButtons.forEach((button) => {
      const active = button.dataset.direbuilderTab === targetId;
      button.classList.toggle('is-active', active);
      button.setAttribute('aria-selected', active ? 'true' : 'false');
    });
    tabPanels.forEach((panel) => {
      panel.classList.toggle('is-active', panel.dataset.direbuilderPanel === targetId);
    });
  }

  function escapeHtml(value) {
    return String(value ?? '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');
  }

  function titleize(value) {
    return String(value || '')
      .replaceAll('_', ' ')
      .replace(/\b\w/g, (match) => match.toUpperCase());
  }

  function slugifyTagValue(value) {
    return String(value || '')
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '');
  }

  function normalizeList(value) {
    if (Array.isArray(value)) {
      return value.map((entry) => String(entry || '').trim()).filter(Boolean);
    }
    if (value == null || value === '') {
      return [];
    }
    return [String(value).trim()].filter(Boolean);
  }

  function getZoneVocabOptions(key) {
    return normalizeList(zoneVocab?.[key]);
  }

  function getRoomTagVocabOptions(key) {
    if (key.startsWith('atmosphere.')) {
      return normalizeList(roomTagVocab?.atmosphere?.[key.split('.')[1]]);
    }
    return normalizeList(roomTagVocab?.room?.[key]);
  }

  function previewBaseForRoom(room) {
    if (!room) {
      return 'Select a room on the map to inspect its description.';
    }
    const savedDescription = String(room.desc || '').trim();
    if (savedDescription) {
      return savedDescription;
    }
    return `${room.name || 'This room'} has not been described yet.`;
  }

  function previewStatesForRoom(room) {
    const previewBase = previewBaseForRoom(room);
    return {
      default: previewBase,
      morning: `${previewBase} Morning trade and opening shutters push the scene toward daily activity.`,
      winter: `${previewBase} Snow and brittle winter air sharpen every surface and mute the wider zone.`,
      evening: `${previewBase} Evening rain turns stone reflective while lamps warm the edges of the street.`,
      night: `${previewBase} Night pressure and guarded movement make the room feel defensive and watched.`,
    };
  }

  function renderIdentity(room) {
    if (!identityFields) {
      return;
    }
    identityFields.innerHTML = `
      <label class="direbuilder-field"><span data-tooltip-field="room.name">Name</span><input type="text" value="${escapeHtml(room?.name || '')}" data-direbuilder-room-field="name"></label>
      <label class="direbuilder-field"><span data-tooltip-field="room.room_id">Room Id</span><input type="text" value="${escapeHtml(room?.id || '')}" readonly></label>
      <label class="direbuilder-field"><span data-tooltip-field="room.environment">Environment</span><input type="text" value="${escapeHtml(titleize(room?.environment || 'unknown'))}" data-direbuilder-room-field="environment"></label>
      <label class="direbuilder-field"><span data-tooltip-field="room.short_desc">Short Description</span><input type="text" value="${escapeHtml(room?.short_desc || '')}" data-direbuilder-room-field="short_desc"></label>
    `;
    attachTooltipIconsIn(identityFields);

    Array.from(identityFields.querySelectorAll('[data-direbuilder-room-field]')).forEach((input) => {
      input.addEventListener('input', function () {
        const currentRoom = getCurrentRoom();
        if (!currentRoom) {
          return;
        }
        const field = input.dataset.direbuilderRoomField;
        if (field === 'environment') {
          currentRoom.environment = String(input.value || '').trim().toLowerCase();
          if (roomEnvironment) {
            roomEnvironment.textContent = titleize(currentRoom.environment || 'unknown');
          }
          updateDirtyIndicator();
          return;
        }
        currentRoom[field] = input.value;
        if (field === 'name' && roomTitle) {
          roomTitle.textContent = input.value || currentRoom.id || 'Unnamed room';
        }
        updateDirtyIndicator();
      });
      input.addEventListener('change', function () {
        const currentRoom = getCurrentRoom();
        if (!currentRoom) {
          return;
        }
        if (input.dataset.direbuilderRoomField === 'environment') {
          currentRoom.environment = String(input.value || '').trim().toLowerCase();
          input.value = titleize(currentRoom.environment || 'unknown');
          if (roomEnvironment) {
            roomEnvironment.textContent = titleize(currentRoom.environment || 'unknown');
          }
        }
        updateDirtyIndicator();
      });
    });
  }

  function renderTags(room) {
    if (!tagsList) {
      return;
    }
    const tagSections = [
      { title: 'Structure', key: 'structure', fieldPath: 'room.tags.structure', values: normalizeList(room?.tags?.structure), multi: false, availableOptions: getRoomTagVocabOptions('structure') },
      { title: 'Specific Function', key: 'specific_function', fieldPath: 'room.tags.specific_function', values: normalizeList(room?.tags?.specific_function), multi: false, availableOptions: getRoomTagVocabOptions('specific_function') },
      { title: 'Named Feature', key: 'named_feature', fieldPath: 'room.tags.named_feature', values: normalizeList(room?.tags?.named_feature), multi: false, availableOptions: getRoomTagVocabOptions('named_feature') },
      { title: 'Condition', key: 'condition', fieldPath: 'room.tags.condition', values: normalizeList(room?.tags?.condition), multi: false, availableOptions: getRoomTagVocabOptions('condition') },
      { title: 'Custom', key: 'custom', fieldPath: 'room.tags.custom', values: normalizeList(room?.tags?.custom), multi: true, availableOptions: [] },
      { title: 'Atmosphere: Materials', key: 'atmosphere.materials', fieldPath: 'room.tags.atmosphere.materials', values: normalizeList(room?.tags?.atmosphere?.materials), multi: true, availableOptions: getRoomTagVocabOptions('atmosphere.materials'), allowCustomInput: true },
      { title: 'Atmosphere: Social Character', key: 'atmosphere.social_character', fieldPath: 'room.tags.atmosphere.social_character', values: normalizeList(room?.tags?.atmosphere?.social_character), multi: true, availableOptions: getRoomTagVocabOptions('atmosphere.social_character'), allowCustomInput: true },
      { title: 'Atmosphere: Surroundings', key: 'atmosphere.surroundings', fieldPath: 'room.tags.atmosphere.surroundings', values: normalizeList(room?.tags?.atmosphere?.surroundings), multi: true, availableOptions: getRoomTagVocabOptions('atmosphere.surroundings'), allowCustomInput: true },
      { title: 'Atmosphere: Sensory', key: 'atmosphere.sensory', fieldPath: 'room.tags.atmosphere.sensory', values: normalizeList(room?.tags?.atmosphere?.sensory), multi: true, availableOptions: getRoomTagVocabOptions('atmosphere.sensory'), allowCustomInput: true },
      { title: 'Atmosphere: Upkeep', key: 'atmosphere.upkeep', fieldPath: 'room.tags.atmosphere.upkeep', values: normalizeList(room?.tags?.atmosphere?.upkeep), multi: false, availableOptions: getRoomTagVocabOptions('atmosphere.upkeep'), allowCustomInput: true },
    ];
    const markup = tagSections.map((section) => {
      const summaryValue = section.values.length ? section.values.map(titleize).join(', ') : '(not set)';
      return `
        <details class="direbuilder-accordion">
          <summary><span data-tooltip-field="${escapeHtml(section.fieldPath)}">${escapeHtml(section.title)}</span><span class="direbuilder-summary-value">${escapeHtml(summaryValue)}</span></summary>
          <div class="direbuilder-accordion-body" data-tag-body="${escapeHtml(section.key)}"></div>
        </details>
      `;
    }).join('');
    tagsList.innerHTML = markup || '<div class="direbuilder-note">No tags available.</div>';
    attachTooltipIconsIn(tagsList);

    function applyTagChange(sectionKey, nextValues) {
      const currentRoom = getCurrentRoom();
      if (!currentRoom) {
        return;
      }
      currentRoom.tags = ensureObject(currentRoom.tags);
      currentRoom.tags.atmosphere = ensureObject(currentRoom.tags.atmosphere);
      if (sectionKey.startsWith('atmosphere.')) {
        const childKey = sectionKey.split('.')[1];
        currentRoom.tags.atmosphere[childKey] = childKey === 'upkeep'
          ? (nextValues[0] || '')
          : nextValues;
      } else if (sectionKey === 'custom') {
        currentRoom.tags.custom = nextValues;
      } else {
        currentRoom.tags[sectionKey] = nextValues[0] || '';
      }
      renderTags(currentRoom);
      updateDirtyIndicator();
    }

    tagSections.forEach((section) => {
      renderChipEditor(tagsList.querySelector(`[data-tag-body="${section.key}"]`), {
        values: section.values,
        availableOptions: section.availableOptions,
        allowMultiple: section.multi,
        placeholder: 'Add value',
        buttonLabel: 'Add',
        allowCustomInput: Boolean(section.allowCustomInput),
        customPlaceholder: 'Add custom...',
        onChange(nextValues) {
          applyTagChange(section.key, nextValues);
        },
      });
    });
  }

  function renderStateful(room) {
    if (roomStates) {
      const states = normalizeList(room?.room_states);
      roomStates.innerHTML = `
        <div class="direbuilder-pill-row">${states.length ? states.map((value) => `<button type="button" class="direbuilder-pill direbuilder-pill-button" data-room-state-remove="${escapeHtml(value)}">${escapeHtml(titleize(value))}<span class="direbuilder-pill-remove">x</span></button>`).join('') : '<span class="direbuilder-note">No room states saved.</span>'}</div>
        <div class="direbuilder-inline-editor"><input class="direbuilder-compact-input" type="text" placeholder="Add room state" data-room-state-input><button class="direbuilder-button direbuilder-button-secondary direbuilder-mini-button" type="button" data-room-state-add>Add</button></div>
      `;
      roomStates.querySelectorAll('[data-room-state-remove]').forEach((button) => {
        button.addEventListener('click', function () {
          const currentRoom = getCurrentRoom();
          if (!currentRoom) {
            return;
          }
          currentRoom.room_states = normalizeList(currentRoom.room_states).filter((value) => value !== button.dataset.roomStateRemove);
          renderStateful(currentRoom);
          updateDirtyIndicator();
        });
      });
      roomStates.querySelector('[data-room-state-add]')?.addEventListener('click', function () {
        const currentRoom = getCurrentRoom();
        const input = roomStates.querySelector('[data-room-state-input]');
        const value = String(input?.value || '').trim();
        if (!currentRoom || !value) {
          return;
        }
        currentRoom.room_states = normalizeList(currentRoom.room_states).concat(value).filter((entry, index, array) => array.indexOf(entry) === index);
        renderStateful(currentRoom);
        updateDirtyIndicator();
      });
    }
    if (statefulDescriptions) {
      const entries = Object.entries(room?.stateful_descs || {});
      statefulDescriptions.innerHTML = `
        ${entries.length ? entries.map(([key, value]) => `<div class="direbuilder-list-row align-start direbuilder-editor-row" data-stateful-row><input class="direbuilder-compact-input" type="text" value="${escapeHtml(key)}" data-stateful-key><textarea class="direbuilder-textarea" data-stateful-value>${escapeHtml(value || '')}</textarea><button class="direbuilder-button direbuilder-button-secondary direbuilder-mini-button" type="button" data-stateful-delete>Delete</button></div>`).join('') : '<div class="direbuilder-note">No stateful descriptions are defined yet.</div>'}
        <div class="direbuilder-inline-editor"><input class="direbuilder-compact-input" type="text" placeholder="State name" data-stateful-new-key><button class="direbuilder-button direbuilder-button-secondary direbuilder-mini-button" type="button" data-stateful-add>Add Custom State</button></div>
      `;
      function syncStatefulDescriptions() {
        const currentRoom = getCurrentRoom();
        if (!currentRoom) {
          return;
        }
        const nextStateful = {};
        statefulDescriptions.querySelectorAll('[data-stateful-row]').forEach((row) => {
          const key = String(row.querySelector('[data-stateful-key]')?.value || '').trim();
          const value = String(row.querySelector('[data-stateful-value]')?.value || '');
          if (key) {
            nextStateful[key] = value;
          }
        });
        currentRoom.stateful_descs = nextStateful;
        updateDirtyIndicator();
      }
      statefulDescriptions.querySelectorAll('[data-stateful-key], [data-stateful-value]').forEach((input) => {
        input.addEventListener('input', syncStatefulDescriptions);
      });
      statefulDescriptions.querySelectorAll('[data-stateful-delete]').forEach((button) => {
        button.addEventListener('click', function () {
          button.closest('[data-stateful-row]')?.remove();
          syncStatefulDescriptions();
          renderStateful(getCurrentRoom());
        });
      });
      statefulDescriptions.querySelector('[data-stateful-add]')?.addEventListener('click', function () {
        const currentRoom = getCurrentRoom();
        const input = statefulDescriptions.querySelector('[data-stateful-new-key]');
        const key = String(input?.value || '').trim();
        if (!currentRoom || !key) {
          return;
        }
        currentRoom.stateful_descs = ensureObject(currentRoom.stateful_descs);
        currentRoom.stateful_descs[key] = currentRoom.stateful_descs[key] || '';
        renderStateful(currentRoom);
        updateDirtyIndicator();
      });
    }
    attachTooltipIconsIn(page);
  }

  function renderConnections(room) {
    if (!connectionsList) {
      return;
    }
    const exits = Object.entries(room?.exits || {});
    const detailsEntries = Object.entries(room?.details || {});
    const ambientMessages = normalizeList(room?.ambient?.messages);
    const ambientDrafts = ensureArray(room?._draftAmbientMessages);
    const ambientRows = ambientMessages.concat(ambientDrafts);
    connectionsList.innerHTML = `
      <div class="direbuilder-section-block">
        <h3 class="direbuilder-section-title"><span data-tooltip-field="room.exits">Exits</span></h3>
        <div class="direbuilder-editor-header-row direbuilder-editor-grid"><span>Direction</span><span>Target Room</span><span data-tooltip-field="room.exit_typeclass">Exit Type</span><span></span></div>
        <div class="direbuilder-list">${exits.length ? exits.map(([direction, payload]) => `<div class="direbuilder-list-row direbuilder-editor-grid" data-exit-row><select data-exit-direction>${makeOptionMarkup(EXIT_DIRECTION_OPTIONS, direction)}</select><input class="direbuilder-compact-input" type="text" value="${escapeHtml(payload?.target || '')}" placeholder="Target room id" data-exit-target><select data-exit-type>${makeOptionMarkup(EXIT_TYPE_OPTIONS, payload?.typeclass || payload?.type || 'typeclasses.exits.Exit')}</select><button class="direbuilder-button direbuilder-button-secondary direbuilder-mini-button" type="button" data-exit-delete>Delete</button></div>`).join('') : '<div class="direbuilder-note">This room has no saved exits.</div>'}</div>
        <button class="direbuilder-button direbuilder-button-secondary direbuilder-mini-button" type="button" data-add-exit>Add Exit</button>
      </div>
      <div class="direbuilder-section-block">
        <h3 class="direbuilder-section-title"><span data-tooltip-field="room.details">Details</span></h3>
        <div class="direbuilder-list">${detailsEntries.length ? detailsEntries.map(([key, value]) => `<div class="direbuilder-list-row align-start direbuilder-editor-row" data-detail-row><input class="direbuilder-compact-input" type="text" value="${escapeHtml(key)}" placeholder="Keyword" data-detail-key><textarea class="direbuilder-textarea" data-detail-value>${escapeHtml(value || '')}</textarea><button class="direbuilder-button direbuilder-button-secondary direbuilder-mini-button" type="button" data-detail-delete>Delete</button></div>`).join('') : '<div class="direbuilder-note">No room details saved.</div>'}</div>
        <div class="direbuilder-inline-editor"><input class="direbuilder-compact-input" type="text" placeholder="New detail keyword" data-detail-new-key><button class="direbuilder-button direbuilder-button-secondary direbuilder-mini-button" type="button" data-detail-add>Add Detail</button></div>
      </div>
      <div class="direbuilder-section-block">
        <h3 class="direbuilder-section-title"><span data-tooltip-field="room.ambient_messages">Ambient Messages</span></h3>
        <label class="direbuilder-field"><span data-tooltip-field="room.ambient_rate">Ambient Rate</span><input class="direbuilder-compact-input" type="number" min="0" value="${escapeHtml(room?.ambient?.rate ?? 0)}" data-ambient-rate></label>
        <div class="direbuilder-list">${ambientRows.length ? ambientRows.map((message) => `<div class="direbuilder-list-row align-start direbuilder-editor-row" data-ambient-row><textarea class="direbuilder-textarea" data-ambient-message>${escapeHtml(message)}</textarea><button class="direbuilder-button direbuilder-button-secondary direbuilder-mini-button" type="button" data-ambient-delete>Delete</button></div>`).join('') : '<div class="direbuilder-note">No ambient messages saved.</div>'}</div>
        <button class="direbuilder-button direbuilder-button-secondary direbuilder-mini-button" type="button" data-ambient-add>Add Ambient Message</button>
      </div>
    `;
    attachTooltipIconsIn(connectionsList);

    function syncConnectionsFromDom() {
      const currentRoom = getCurrentRoom();
      if (!currentRoom) {
        return;
      }
      const nextExits = {};
      connectionsList.querySelectorAll('[data-exit-row]').forEach((row) => {
        const direction = String(row.querySelector('[data-exit-direction]')?.value || '').trim().toLowerCase();
        const target = String(row.querySelector('[data-exit-target]')?.value || '').trim();
        const typeclass = String(row.querySelector('[data-exit-type]')?.value || 'typeclasses.exits.Exit').trim();
        if (direction) {
          nextExits[direction] = { target, typeclass, speed: '', travel_time: 0 };
        }
      });
      const nextDetails = {};
      connectionsList.querySelectorAll('[data-detail-row]').forEach((row) => {
        const key = String(row.querySelector('[data-detail-key]')?.value || '').trim();
        const value = String(row.querySelector('[data-detail-value]')?.value || '');
        if (key) {
          nextDetails[key] = value;
        }
      });
      const nextAmbientMessages = [];
      const nextAmbientDrafts = [];
      connectionsList.querySelectorAll('[data-ambient-row]').forEach((row) => {
        const value = String(row.querySelector('[data-ambient-message]')?.value || '');
        if (value) {
          nextAmbientMessages.push(value.trim());
        } else {
          nextAmbientDrafts.push('');
        }
      });
      currentRoom.exits = nextExits;
      currentRoom.details = nextDetails;
      currentRoom.ambient = {
        rate: Number(connectionsList.querySelector('[data-ambient-rate]')?.value || 0) || 0,
        messages: nextAmbientMessages,
      };
      currentRoom._draftAmbientMessages = nextAmbientDrafts;
      updateDirtyIndicator();
    }

    connectionsList.querySelectorAll('[data-exit-direction], [data-exit-target], [data-exit-type], [data-detail-key], [data-detail-value], [data-ambient-rate], [data-ambient-message]').forEach((input) => {
      input.addEventListener('input', syncConnectionsFromDom);
      input.addEventListener('change', syncConnectionsFromDom);
    });
    connectionsList.querySelectorAll('[data-exit-delete], [data-detail-delete], [data-ambient-delete]').forEach((button) => {
      button.addEventListener('click', function () {
        button.closest('[data-exit-row], [data-detail-row], [data-ambient-row]')?.remove();
        syncConnectionsFromDom();
        renderConnections(getCurrentRoom());
      });
    });
    connectionsList.querySelector('[data-add-exit]')?.addEventListener('click', function () {
      const currentRoom = getCurrentRoom();
      if (!currentRoom) {
        return;
      }
      let direction = 'north';
      while (currentRoom.exits[direction]) {
        direction = `${direction}-alt`;
      }
      currentRoom.exits[direction] = { target: '', typeclass: 'typeclasses.exits.Exit', speed: '', travel_time: 0 };
      renderConnections(currentRoom);
      updateDirtyIndicator();
    });
    connectionsList.querySelector('[data-detail-add]')?.addEventListener('click', function () {
      const currentRoom = getCurrentRoom();
      const input = connectionsList.querySelector('[data-detail-new-key]');
      const key = String(input?.value || '').trim();
      if (!currentRoom || !key) {
        return;
      }
      currentRoom.details[key] = currentRoom.details[key] || '';
      renderConnections(currentRoom);
      updateDirtyIndicator();
    });
    connectionsList.querySelector('[data-ambient-add]')?.addEventListener('click', function () {
      const currentRoom = getCurrentRoom();
      if (!currentRoom) {
        return;
      }
      currentRoom._draftAmbientMessages = ensureArray(currentRoom._draftAmbientMessages).concat('');
      renderConnections(currentRoom);
      updateDirtyIndicator();
    });
  }

  function renderPopulation(room) {
    if (populationNpcs) {
      const npcs = getCurrentRoomPlacements('npcs', room?.id).concat(ensureArray(room?._draftNpcRows));
      populationNpcs.innerHTML = `
        <div class="direbuilder-editor-header-row"><span data-tooltip-field="room.npcs">NPC Placements</span></div>
        <div class="direbuilder-list">${npcs.length ? npcs.map((entry, index) => `<div class="direbuilder-list-row direbuilder-editor-grid" data-population-npc-row><input class="direbuilder-compact-input" type="text" value="${escapeHtml(entry?.id || '')}" placeholder="NPC id" data-population-npc-id><input class="direbuilder-compact-input" type="text" value="${escapeHtml(entry?.typeclass || '')}" placeholder="Typeclass" data-population-npc-typeclass><button class="direbuilder-button direbuilder-button-secondary direbuilder-mini-button" type="button" data-population-up="${index}">Up</button><button class="direbuilder-button direbuilder-button-secondary direbuilder-mini-button" type="button" data-population-down="${index}">Down</button><button class="direbuilder-button direbuilder-button-secondary direbuilder-mini-button" type="button" data-population-delete>Delete</button></div>`).join('') : '<span class="direbuilder-note">No NPC placements in this room.</span>'}</div>
        <button class="direbuilder-button direbuilder-button-secondary direbuilder-mini-button" type="button" data-population-add-npc>Add NPC</button>
      `;
      attachTooltipIconsIn(populationNpcs);
    }
    if (populationItems) {
      const items = getCurrentRoomPlacements('items', room?.id).concat(ensureArray(room?._draftItemRows));
      populationItems.innerHTML = `
        <div class="direbuilder-editor-header-row"><span data-tooltip-field="room.items">Item Placements</span></div>
        <div class="direbuilder-list">${items.length ? items.map((entry, index) => `<div class="direbuilder-list-row direbuilder-editor-grid" data-population-item-row><input class="direbuilder-compact-input" type="text" value="${escapeHtml(entry?.id || '')}" placeholder="Item id" data-population-item-id><input class="direbuilder-compact-input" type="number" min="1" value="${escapeHtml(entry?.count ?? 1)}" data-population-item-count><button class="direbuilder-button direbuilder-button-secondary direbuilder-mini-button" type="button" data-population-item-up="${index}">Up</button><button class="direbuilder-button direbuilder-button-secondary direbuilder-mini-button" type="button" data-population-item-down="${index}">Down</button><button class="direbuilder-button direbuilder-button-secondary direbuilder-mini-button" type="button" data-population-item-delete>Delete</button></div>`).join('') : '<div class="direbuilder-note">No item placements in this room.</div>'}</div>
        <button class="direbuilder-button direbuilder-button-secondary direbuilder-mini-button" type="button" data-population-add-item>Add Item</button>
      `;
      attachTooltipIconsIn(populationItems);
    }

    function readNpcRows() {
      return Array.from(populationNpcs.querySelectorAll('[data-population-npc-row]')).map((row) => ({
        id: String(row.querySelector('[data-population-npc-id]')?.value || '').trim(),
        typeclass: String(row.querySelector('[data-population-npc-typeclass]')?.value || '').trim(),
        prototype: null,
      }));
    }

    function readItemRows() {
      return Array.from(populationItems.querySelectorAll('[data-population-item-row]')).map((row) => ({
        id: String(row.querySelector('[data-population-item-id]')?.value || '').trim(),
        count: Number(row.querySelector('[data-population-item-count]')?.value || 1) || 1,
        typeclass: '',
        prototype: null,
      }));
    }

    function move(list, fromIndex, toIndex) {
      if (toIndex < 0 || toIndex >= list.length || fromIndex === toIndex) {
        return list;
      }
      const copy = list.slice();
      const [entry] = copy.splice(fromIndex, 1);
      copy.splice(toIndex, 0, entry);
      return copy;
    }

    populationNpcs?.querySelectorAll('[data-population-npc-id], [data-population-npc-typeclass]').forEach((input) => {
      input.addEventListener('input', function () {
        const rows = readNpcRows();
        room._draftNpcRows = rows.filter((entry) => !entry.id);
        setCurrentRoomPlacements('npcs', room?.id, rows.filter((entry) => entry.id));
        updateDirtyIndicator();
      });
    });
    populationItems?.querySelectorAll('[data-population-item-id], [data-population-item-count]').forEach((input) => {
      input.addEventListener('input', function () {
        const rows = readItemRows();
        room._draftItemRows = rows.filter((entry) => !entry.id);
        setCurrentRoomPlacements('items', room?.id, rows.filter((entry) => entry.id));
        updateDirtyIndicator();
      });
    });
    populationNpcs?.querySelectorAll('[data-population-delete]').forEach((button) => {
      button.addEventListener('click', function () {
        button.closest('[data-population-npc-row]')?.remove();
        const rows = readNpcRows();
        room._draftNpcRows = rows.filter((entry) => !entry.id);
        setCurrentRoomPlacements('npcs', room?.id, rows.filter((entry) => entry.id));
        renderPopulation(getCurrentRoom());
        updateDirtyIndicator();
      });
    });
    populationItems?.querySelectorAll('[data-population-item-delete]').forEach((button) => {
      button.addEventListener('click', function () {
        button.closest('[data-population-item-row]')?.remove();
        const rows = readItemRows();
        room._draftItemRows = rows.filter((entry) => !entry.id);
        setCurrentRoomPlacements('items', room?.id, rows.filter((entry) => entry.id));
        renderPopulation(getCurrentRoom());
        updateDirtyIndicator();
      });
    });
    populationNpcs?.querySelector('[data-population-add-npc]')?.addEventListener('click', function () {
      room._draftNpcRows = ensureArray(room._draftNpcRows).concat({ id: '', typeclass: '', prototype: null });
      renderPopulation(getCurrentRoom());
      updateDirtyIndicator();
    });
    populationItems?.querySelector('[data-population-add-item]')?.addEventListener('click', function () {
      room._draftItemRows = ensureArray(room._draftItemRows).concat({ id: '', count: 1, typeclass: '', prototype: null });
      renderPopulation(getCurrentRoom());
      updateDirtyIndicator();
    });
    populationNpcs?.querySelectorAll('[data-population-up], [data-population-down]').forEach((button) => {
      button.addEventListener('click', function () {
        const entries = readNpcRows();
        const index = Number(button.dataset.populationUp ?? button.dataset.populationDown);
        const targetIndex = button.hasAttribute('data-population-up') ? index - 1 : index + 1;
        const movedEntries = move(entries, index, targetIndex);
        room._draftNpcRows = movedEntries.filter((entry) => !entry.id);
        setCurrentRoomPlacements('npcs', room?.id, movedEntries.filter((entry) => entry.id));
        renderPopulation(getCurrentRoom());
        updateDirtyIndicator();
      });
    });
    populationItems?.querySelectorAll('[data-population-item-up], [data-population-item-down]').forEach((button) => {
      button.addEventListener('click', function () {
        const entries = readItemRows();
        const index = Number(button.dataset.populationItemUp ?? button.dataset.populationItemDown);
        const targetIndex = button.hasAttribute('data-population-item-up') ? index - 1 : index + 1;
        const movedEntries = move(entries, index, targetIndex);
        room._draftItemRows = movedEntries.filter((entry) => !entry.id);
        setCurrentRoomPlacements('items', room?.id, movedEntries.filter((entry) => entry.id));
        renderPopulation(getCurrentRoom());
        updateDirtyIndicator();
      });
    });
  }

  function renderRoomEditor(roomId) {
    const room = getCurrentRoom(roomId);
    if (isGeneratingDescription() && room && String(room.id || '') !== String(state.generationRoomId || '')) {
      updateDescriptionGenerationUi(getCurrentRoom(state.generationRoomId));
      return;
    }
    state.currentRoomId = room ? String(room.id || '') : '';
    if (!room) {
      if (roomTitle) {
        roomTitle.textContent = 'Select a room on the map';
      }
      if (roomEnvironment) {
        roomEnvironment.textContent = 'No selection';
      }
      if (roomZone) {
        roomZone.textContent = workingZone?.zone_id || 'No zone';
      }
      if (roomEmpty) {
        roomEmpty.hidden = false;
      }
      if (roomEditorContent) {
        roomEditorContent.hidden = true;
      }
      if (renderedPreview) {
        renderedPreview.textContent = 'Select a room on the map to inspect its description.';
      }
      if (manualDescription) {
        manualDescription.value = 'Select a room on the map to inspect its description.';
      }
      updateDescriptionGenerationUi(null);
      return;
    }

    if (roomTitle) {
      roomTitle.textContent = room.name || room.id || 'Unnamed room';
    }
    if (roomEnvironment) {
      roomEnvironment.textContent = titleize(room.environment || 'unknown');
    }
    if (roomZone) {
      roomZone.textContent = room.zone_id || workingZone?.zone_id || 'No zone';
    }
    if (roomEmpty) {
      roomEmpty.hidden = true;
    }
    if (roomEditorContent) {
      roomEditorContent.hidden = false;
    }

    renderIdentity(room);
    renderTags(room);
    renderStateful(room);
    renderConnections(room);
    renderPopulation(room);

    const previews = previewStatesForRoom(room);
    if (renderedPreview) {
      renderedPreview.textContent = previews[state.previewMode] || previews.default;
    }
    if (manualDescription) {
      manualDescription.value = String(room.desc || '').trim() || 'No saved room description yet.';
      manualDescription.readOnly = false;
    }
    updateDescriptionGenerationUi(room);
  }

  function closeOverflow() {
    if (!overflowMenu || !overflowTrigger) {
      return;
    }
    overflowMenu.hidden = true;
    overflowTrigger.setAttribute('aria-expanded', 'false');
  }

  function toggleOverflow() {
    if (!overflowMenu || !overflowTrigger) {
      return;
    }
    if (isOperationInProgress()) {
      return;
    }
    const expanded = overflowMenu.hidden;
    overflowMenu.hidden = !expanded;
    overflowTrigger.setAttribute('aria-expanded', expanded ? 'true' : 'false');
  }

  function showToast(message) {
    if (!toastStack) {
      return;
    }
    const toast = document.createElement('div');
    toast.className = 'direbuilder-toast';
    toast.textContent = message;
    toastStack.appendChild(toast);
    window.setTimeout(() => toast.remove(), 2200);
  }

  function generateDescriptionForCurrentRoom() {
    const room = getCurrentRoom();
    const zoneId = String(workingZone?.zone_id || '').trim();
    const roomId = String(room?.id || '').trim();
    if (!room || !zoneId || !roomId) {
      return Promise.resolve(null);
    }
    if (isGeneratingDescription()) {
      return state.generationPromise || Promise.resolve(null);
    }

    state.generationState = 'generating';
    state.generationRoomId = roomId;
    state.generationPromise = fetchWithTimeout(buildGenerateDescriptionUrl(zoneId, roomId), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ room: cloneData(room) }),
    }, 45000).then(async (response) => {
      if (!response.ok) {
        const failure = await parseGenerationFailure(response);
        const error = new Error(failure.message);
        error.code = failure.code;
        error.retriable = failure.retriable;
        throw error;
      }
      const payload = await response.json();
      const targetRoom = getCurrentRoom(roomId) || getRoomsById().get(roomId) || null;
      if (!targetRoom) {
        throw new Error('Description generated, but the target room is no longer available in the working zone.');
      }
      targetRoom.desc = String(payload?.pass_2 || '').trim();
      state.lastGenerationTelemetryByRoom[roomId] = cloneData(ensureObject(payload?.telemetry));
      clearSaveErrorBanner();
      if (String(state.currentRoomId || '') === roomId) {
        renderRoomEditor(roomId);
      } else {
        updateDescriptionGenerationUi(targetRoom);
      }
      updateDirtyIndicator();
      showToast('Description generated. Review and Save Zone to keep it.');
      return payload;
    }).catch((error) => {
      const message = String(error?.message || 'Description generation failed unexpectedly. Try again. If this persists, check the server logs.');
      showSaveErrorBanner(message, 'Generation Error');
      showToast(message);
      throw error;
    }).finally(() => {
      state.generationState = 'idle';
      state.generationPromise = null;
      state.generationRoomId = null;
      updateDescriptionGenerationUi(getCurrentRoom());
    });

    updateDescriptionGenerationUi(room);
    return state.generationPromise;
  }

  function closeModal() {
    if (!modalOverlay || !modalCard) {
      return;
    }
    delete modalOverlay.dataset.pending;
    modalOverlay.hidden = true;
    modalOverlay.style.display = 'none';
    modalCard.innerHTML = '';
  }

  function showModal(config) {
    if (!modalOverlay || !modalCard) {
      return;
    }
    const cancelLabel = config.cancelLabel || 'Cancel';
    modalCard.innerHTML = `
      <div class="direbuilder-modal-kicker">${config.kicker}</div>
      <h3 class="direbuilder-modal-title" id="direbuilder-modal-title">${config.title}</h3>
      <div class="direbuilder-modal-body">${config.body.map((line) => `<p>${line}</p>`).join('')}</div>
      <div class="direbuilder-modal-actions">
        <button type="button" class="direbuilder-button ${config.cancelClassName || 'direbuilder-modal-cancel'}" data-modal-cancel>${cancelLabel}</button>
        ${config.actions.map((action) => `<button type="button" class="direbuilder-button ${action.className || 'direbuilder-button-secondary'}" data-modal-action="${action.id}">${action.label}</button>`).join('')}
      </div>
    `;
    modalOverlay.hidden = false;
    modalOverlay.style.display = 'flex';

    modalCard.querySelector('[data-modal-cancel]')?.addEventListener('click', function () {
      if (modalOverlay?.dataset.pending === 'true') {
        return;
      }
      closeModal();
      config.onCancel?.();
    });
    config.actions.forEach((action) => {
      const actionButton = modalCard.querySelector(`[data-modal-action="${action.id}"]`);
      actionButton?.addEventListener('click', function () {
        const cancelButton = modalCard.querySelector('[data-modal-cancel]');
        const originalLabel = actionButton.textContent;
        const result = action.onClick?.({
          actionButton,
          cancelButton,
          closeModal,
        });
        if (result && typeof result.then === 'function') {
          if (action.pendingLabel) {
            actionButton.textContent = action.pendingLabel;
          }
          if (action.lockModalOnPending) {
            modalOverlay.dataset.pending = 'true';
            actionButton.disabled = true;
            if (cancelButton) {
              cancelButton.disabled = true;
            }
          }
          result.then(() => {
            closeModal();
          }).catch(() => {
            if (modalOverlay?.isConnected) {
              delete modalOverlay.dataset.pending;
            }
            if (actionButton.isConnected) {
              actionButton.disabled = false;
              actionButton.textContent = originalLabel;
            }
            if (cancelButton?.isConnected) {
              cancelButton.disabled = false;
            }
          });
          return;
        }
        closeModal();
      });
    });
    modalCard.querySelector('[data-modal-cancel]')?.focus();
  }

  function attemptZoneSwitch(nextZoneId) {
    const targetZoneId = String(nextZoneId || '').trim();
    if (!targetZoneId) {
      return false;
    }
    if (isOperationInProgress()) {
      if (zoneSelect) {
        zoneSelect.value = String(page.dataset.currentZoneId || workingZone?.zone_id || '');
      }
      showToast(getSaveFailureMessage('operation_in_progress'));
      return false;
    }
    if (isDirty()) {
      if (zoneSelect) {
        zoneSelect.value = String(page.dataset.currentZoneId || workingZone?.zone_id || '');
      }
      showModal({
        kicker: 'Unsaved Changes',
        title: `You have unsaved changes in ${workingZone?.name || 'this zone'}.`,
        body: ['Save changes before switching zones, discard them, or cancel to stay here.'],
        actions: [
          { id: 'save-switch', label: 'Save & Switch', className: 'direbuilder-button-secondary', onClick: () => { saveWorkingZone({ silentSuccessToast: true }).then(() => { window.location.href = `/direbuilder/?zone=${encodeURIComponent(targetZoneId)}`; }).catch(() => {}); } },
          { id: 'discard-switch', label: 'Discard & Switch', onClick: () => { window.location.href = `/direbuilder/?zone=${encodeURIComponent(targetZoneId)}`; } },
        ],
      });
      return false;
    }
    window.location.href = `/direbuilder/?zone=${encodeURIComponent(targetZoneId)}`;
    return true;
  }

  function mountMap() {
    const root = document.getElementById('builder-reactflow-root');
    if (!root || !workingZone || !window.DragonsireBuilderReactFlow?.mountBuilderReactFlow) {
      return;
    }
    // Reuse the existing builder bridge callback rather than inventing a second
    // selection channel. React Flow already reports selectedRoomId here.
    window.DragonsireBuilderReactFlow.mountBuilderReactFlow(root, {
      zone: workingZone,
      zonePrefix: String(page.dataset.currentZoneId || 'ZONE').toUpperCase(),
      selectedRoomId: state.currentRoomId || null,
      viewportRequest: { type: 'fit', token: 1 },
      npcCatalog: {},
      onBuilderStateChange: ({ selectedRoomId }) => {
        if (isGeneratingDescription()) {
          return;
        }
        renderRoomEditor(selectedRoomId || null);
      },
      onRoomActivate: () => false,
    });
  }

  tabButtons.forEach((button) => {
    button.addEventListener('click', function () {
      setTab(button.dataset.direbuilderTab);
    });
  });

  if (previewSelect && renderedPreview) {
    previewSelect.addEventListener('change', function () {
      state.previewMode = String(previewSelect.value || 'default');
      const room = getCurrentRoom();
      const previews = previewStatesForRoom(room);
      renderedPreview.textContent = previews[state.previewMode] || previews.default;
    });
  }

  generateDescriptionButton?.addEventListener('click', function () {
    generateDescriptionForCurrentRoom().catch(() => {});
  });

  saveZoneButton?.addEventListener('click', function () {
    if (isOperationInProgress()) {
      return;
    }
    saveWorkingZone().catch(() => {});
  });

  saveErrorDismiss?.addEventListener('click', function () {
    clearSaveErrorBanner();
  });

  zoneVoiceNotes?.addEventListener('input', function () {
    getGenerationContext().voice = String(zoneVoiceNotes.value || '');
    updateDirtyIndicator();
  });

  manualDescription?.addEventListener('input', function () {
    const currentRoom = getCurrentRoom();
    if (!currentRoom) {
      return;
    }
    currentRoom.desc = String(manualDescription.value || '');
    const previews = previewStatesForRoom(currentRoom);
    if (renderedPreview) {
      renderedPreview.textContent = previews[state.previewMode] || previews.default;
    }
    updateDirtyIndicator();
  });
  zoneSelect?.addEventListener('change', function (event) {
    const nextZoneId = String(zoneSelect.value || '').trim();
    if (!nextZoneId) {
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    event.stopImmediatePropagation?.();
    attemptZoneSwitch(nextZoneId);
  });

  window.addEventListener('beforeunload', function (event) {
    if (!isDirty()) {
      return;
    }
    event.preventDefault();
    event.returnValue = '';
  });

  overflowTrigger?.addEventListener('click', toggleOverflow);
  document.getElementById('direbuilder-new-zone')?.addEventListener('click', function () {
    closeOverflow();
    showToast('New Zone is not wired in Phase 1.');
  });
  discardButton?.addEventListener('click', function () {
    closeOverflow();
    if (discardButton.disabled) {
      return;
    }
    showModal({
      kicker: 'Discard Changes',
      title: 'Discard Changes?',
      body: ['You have unsaved changes in this zone. Discarding now will permanently lose those edits and reload the zone from disk.'],
      cancelLabel: 'Cancel',
      cancelClassName: 'direbuilder-button-secondary direbuilder-modal-cancel',
      actions: [{
        id: 'discard',
        label: 'Discard Changes',
        className: 'direbuilder-button-primary',
        pendingLabel: 'Discarding...',
        lockModalOnPending: true,
        onClick: () => discardWorkingZone(),
      }],
    });
  });
  hotLoadButton?.addEventListener('click', function () {
    closeOverflow();
    if (hotLoadButton.disabled) {
      return;
    }
    showModal({
      kicker: 'Hot Load',
      title: isDirty() ? 'Save and Apply to Live Game?' : 'Apply Zone to Live Game?',
      body: [isDirty()
        ? 'You have unsaved changes. Hot Load will save your edits to disk first, then refresh the running game. Connected players may notice runtime objects (NPCs and items) respawn. Removed rooms will remain in the live game until full server restart.'
        : 'Hot Load will refresh this zone in the running game. Connected players may notice runtime objects (NPCs and items) respawn. Removed rooms will remain in the live game until full server restart.'],
      cancelLabel: 'Cancel',
      cancelClassName: 'direbuilder-button-secondary direbuilder-modal-cancel',
      actions: [{
        id: 'hotload',
        label: isDirty() ? 'Save & Hot Load' : 'Hot Load',
        className: 'direbuilder-button-primary',
        pendingLabel: isDirty() ? 'Saving & Hot Loading...' : 'Hot Loading...',
        lockModalOnPending: true,
        onClick: () => hotLoadCurrentZone(),
      }],
    });
  });
  document.getElementById('direbuilder-delete-zone')?.addEventListener('click', function () {
    closeOverflow();
    showModal({
      kicker: `Remove Zone: ${currentZone?.name || 'Current Zone'}`,
      title: 'How would you like to remove this zone?',
      body: ['Archive keeps the zone data and removes it from the live world.', 'Delete permanently removes the zone and all its data.'],
      actions: [
        { id: 'archive', label: 'Archive Zone', onClick: () => showToast('Archive is not wired in Phase 1.') },
        { id: 'delete', label: 'Delete Zone', className: 'direbuilder-button-secondary', onClick: () => showToast('Delete is not wired in Phase 1.') },
      ],
    });
  });

  document.addEventListener('click', function (event) {
    if (!overflowMenu || !overflowTrigger || overflowMenu.hidden) {
      return;
    }
    if (!overflowMenu.contains(event.target) && !overflowTrigger.contains(event.target)) {
      closeOverflow();
    }
  });

  modalOverlay?.addEventListener('click', function (event) {
    if (event.target === modalOverlay) {
      if (modalOverlay?.dataset.pending === 'true') {
        return;
      }
      closeModal();
    }
  });

  document.addEventListener('keydown', function (event) {
    if (modalOverlay?.hidden) {
      if (event.key === 'Escape') {
        closeOverflow();
      }
      return;
    }
    if (event.key === 'Escape') {
      if (modalOverlay?.dataset.pending === 'true') {
        return;
      }
      event.preventDefault();
      closeModal();
    }
  });

  if (modalOverlay) {
    modalOverlay.hidden = true;
    modalOverlay.style.display = 'none';
  }

  window.DireBuilderPageApi = {
    attemptZoneSwitch,
    isDirty,
    saveWorkingZone,
    discardWorkingZone,
    hotLoadCurrentZone,
    getSaveState() {
      return state.saveState;
    },
    getLastSaveError() {
      return state.lastSaveError;
    },
    getDiscardState() {
      return state.discardState;
    },
    getLastDiscardError() {
      return state.lastDiscardError;
    },
    getHotLoadState() {
      return state.hotLoadState;
    },
    getLastHotLoadError() {
      return state.lastHotLoadError;
    },
    getLastHotLoadSummary() {
      return state.lastHotLoadSummary;
    },
    getDirtyState() {
      return isDirty();
    },
  };

  setTab('identity');
  renderRoomEditor(state.currentRoomId || null);
  renderZoneEditor();
  attachTooltipIconsIn(page);
  updateDescriptionGenerationUi(getCurrentRoom());
  updateDirtyIndicator();
  mountMap();
}());
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
  const zoneScript = document.getElementById('direbuilder-zone-data');
  const currentZone = zoneScript ? JSON.parse(zoneScript.textContent || 'null') : null;
  const previewBase = (renderedPreview?.textContent || '').trim();

  const previewStates = {
    default: previewBase,
    morning: `${previewBase} Morning trade and opening shutters push the scene toward daily activity.`,
    winter: `${previewBase} Snow and brittle winter air sharpen every surface and mute the wider zone.`,
    evening: `${previewBase} Evening rain turns stone reflective while lamps warm the edges of the street.`,
    night: `${previewBase} Night pressure and guarded movement make the room feel defensive and watched.`,
  };

  function setTab(targetId) {
    tabButtons.forEach((button) => {
      const active = button.dataset.direbuilderTab === targetId;
      button.classList.toggle('is-active', active);
      button.setAttribute('aria-selected', active ? 'true' : 'false');
    });
    tabPanels.forEach((panel) => {
      panel.classList.toggle('is-active', panel.dataset.direbuilderPanel === targetId);
    });
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

  function closeModal() {
    if (!modalOverlay || !modalCard) {
      return;
    }
    modalOverlay.hidden = true;
    modalOverlay.style.display = 'none';
    modalCard.innerHTML = '';
  }

  function showModal(config) {
    if (!modalOverlay || !modalCard) {
      return;
    }
    modalCard.innerHTML = `
      <div class="direbuilder-modal-kicker">${config.kicker}</div>
      <h3 class="direbuilder-modal-title" id="direbuilder-modal-title">${config.title}</h3>
      <div class="direbuilder-modal-body">${config.body.map((line) => `<p>${line}</p>`).join('')}</div>
      <div class="direbuilder-modal-actions">
        <button type="button" class="direbuilder-button direbuilder-modal-cancel" data-modal-cancel>Cancel</button>
        ${config.actions.map((action) => `<button type="button" class="direbuilder-button ${action.className || 'direbuilder-button-secondary'}" data-modal-action="${action.id}">${action.label}</button>`).join('')}
      </div>
    `;
    modalOverlay.hidden = false;
    modalOverlay.style.display = 'flex';

    modalCard.querySelector('[data-modal-cancel]')?.addEventListener('click', closeModal);
    config.actions.forEach((action) => {
      modalCard.querySelector(`[data-modal-action="${action.id}"]`)?.addEventListener('click', function () {
        closeModal();
        action.onClick?.();
      });
    });
    modalCard.querySelector('[data-modal-cancel]')?.focus();
  }

  function mountMap() {
    const root = document.getElementById('builder-reactflow-root');
    if (!root || !currentZone || !window.DragonsireBuilderReactFlow?.mountBuilderReactFlow) {
      return;
    }
    window.DragonsireBuilderReactFlow.mountBuilderReactFlow(root, {
      zone: currentZone,
      zonePrefix: String(page.dataset.currentZoneId || 'ZONE').toUpperCase(),
      selectedRoomId: String(currentZone.rooms?.[0]?.id || ''),
      viewportRequest: { type: 'fit', token: 1 },
      npcCatalog: {},
      onBuilderStateChange: () => {},
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
      renderedPreview.textContent = previewStates[previewSelect.value] || previewStates.default;
    });
  }

  zoneSelect?.addEventListener('change', function () {
    const nextZoneId = String(zoneSelect.value || '').trim();
    if (!nextZoneId) {
      return;
    }
    window.location.href = `/direbuilder/?zone=${encodeURIComponent(nextZoneId)}`;
  });

  overflowTrigger?.addEventListener('click', toggleOverflow);
  document.getElementById('direbuilder-new-zone')?.addEventListener('click', function () {
    closeOverflow();
    showToast('New Zone is not wired in Phase 1.');
  });
  document.getElementById('direbuilder-discard')?.addEventListener('click', function () {
    closeOverflow();
    showModal({
      kicker: 'Discard Unsaved Changes?',
      title: `Reload ${currentZone?.name || 'current zone'} from disk?`,
      body: ['All unsaved in-browser edits will be lost.', 'The live game will not be affected.'],
      actions: [{ id: 'discard', label: 'Discard Changes' }],
    });
  });
  document.getElementById('direbuilder-hot-load')?.addEventListener('click', function () {
    showModal({
      kicker: 'Hot Load To Live Game',
      title: `Push the saved version of ${currentZone?.name || 'this zone'} to the live running game?`,
      body: ['Players in this zone will see the saved version on their next look.', 'Unsaved in-browser changes are not included in Phase 1.'],
      actions: [{ id: 'hotload', label: 'Push To Live' }],
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
    if (event.key === 'Escape' || event.key === 'Enter') {
      event.preventDefault();
      closeModal();
    }
  });

  if (modalOverlay) {
    modalOverlay.hidden = true;
    modalOverlay.style.display = 'none';
  }

  setTab('identity');
  mountMap();
}());
class InjuryPresenter:

	@staticmethod
	def render_apply_wound(event):
		kind = str(event.get("kind", "") or "")
		part_display = str(event.get("part_display", "part") or "part")
		if kind == "badly_damaged":
			return [f"Your {part_display} is badly damaged!"]
		if kind == "scar_gain":
			return [f"The hurt leaves lasting damage in your {part_display}."]
		return []

	@staticmethod
	def render_bleed_tick(event):
		kind = str(event.get("kind", "tick") or "tick")
		if kind == "death_guard":
			return ["Your returning life falters, but the rite holds for one heartbeat."]
		if kind != "tick":
			return []
		lines = ["You bleed from your wounds."]
		if bool(event.get("heavy", False)):
			lines.append("You are bleeding heavily!")
		return lines

	@staticmethod
	def render_stabilize(event):
		part_display = str(event.get("part_display", "part") or "part")
		return [f"Your {part_display} is steadied and bound."]

	@staticmethod
	def render_heal(event):
		if str(event.get("kind", "") or "") == "natural_recovery":
			return []
		part_display = str(event.get("part_display", "part") or "part")
		return [f"Your {part_display} eases a little."]

	@staticmethod
	def render_worsen(event):
		kind = str(event.get("kind", "") or "")
		if kind == "critical_condition":
			return ["You are in critical condition!"]
		if kind == "bleed_resumed":
			part_display = str(event.get("part_display", "part") or "part")
			return [f"Your {part_display} begins bleeding again!"]
		return []

	@staticmethod
	def render_bleed_state(event):
		new_state = str(event.get("new_state", "none") or "none")
		if new_state == "none":
			return ["Your bleeding has stopped."]
		if new_state == "light":
			return ["You are bleeding."]
		if new_state == "moderate":
			return ["Your wounds are bleeding steadily."]
		if new_state == "severe":
			return ["Your wounds are bleeding heavily."]
		if new_state == "critical":
			return ["Blood is pouring from your wounds!"]
		return []

	@staticmethod
	def render_events(events):
		lines = []
		for event in list(events or []):
			event_name = str(event.get("event", "") or "")
			if event_name == "apply_wound":
				lines.extend(InjuryPresenter.render_apply_wound(event))
			elif event_name == "bleed_tick":
				lines.extend(InjuryPresenter.render_bleed_tick(event))
			elif event_name == "stabilize":
				lines.extend(InjuryPresenter.render_stabilize(event))
			elif event_name == "heal":
				lines.extend(InjuryPresenter.render_heal(event))
			elif event_name == "worsen":
				lines.extend(InjuryPresenter.render_worsen(event))
			elif event_name == "bleed_state":
				lines.extend(InjuryPresenter.render_bleed_state(event))
		return lines

	@staticmethod
	def render_result(result):
		data = dict(getattr(result, "data", {}) or {})
		return InjuryPresenter.render_events(data.get("injury_events", []))

	@staticmethod
	def present_result(target, result):
		if target is None:
			return []
		lines = InjuryPresenter.render_result(result)
		for line in lines:
			target.msg(line)
		return lines

	@staticmethod
	def present_events(target, events):
		if target is None:
			return []
		lines = InjuryPresenter.render_events(events)
		for line in lines:
			target.msg(line)
		return lines
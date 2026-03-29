extends RichTextLabel


func add_line(text: String) -> void:
	append_text(text + "\n")
	scroll_to_line(get_line_count())
def get_note(store, note_id):
	note = store.get(note_id)
	if note is None:
		return respond(404, "missing")
	return respond(200, note)


def put_note(store, note_id, body):
	note = store.get(note_id)
	if note is None:
		return respond(404, "missing")
	return respond(200, note)


LIMIT = 5 < 10  # a lone CR follows this commentand this text sits after it

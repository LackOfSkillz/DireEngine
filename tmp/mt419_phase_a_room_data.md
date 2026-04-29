# MT-419 Phase A Room Data Check

Endpoint verification for MT-419 will use `http://127.0.0.1:1234`.
The `/v1/models` response included `qwen2.5-14b-instruct`.

## amberwick-lane-western-run-4213-4213-4213

Complete YAML entry:

```yaml
- id: amberwick-lane-western-run-4213-4213-4213
  name: Amberwick Lane, Western Run
  typeclass: typeclasses.rooms_extended.ExtendedDireRoom
  short_desc: null
  desc: 'Amberwick Lane threads east and west through the district, a lived-in lane
    of shopfronts, side doors, and close-built eaves. The lane is settled but still
    alert here, close enough to one end that arrivals and departures shape the mood.
    The scents here are clean by city measure: rain on stone, banked hearths, horses
    kept at a remove, and trimmed greenery from private courts. Boundary stones, walls,
    or the edge of a distinct enclave make this stretch feel nearer the city''s margin
    than its heart. Nearby, Residental Cloister arch to To gives this stretch of the
    city a more distinct identity. The surrounding facades feel more deliberate here,
    with cleaner stonework and a quieter civic order.'
  stateful_descs: {}
  details: {}
  room_states: []
  ambient:
    rate: 0
    messages: []
  environment: city
  zone_id: new_landing
  map:
    x: 200
    y: 132
    layer: 0
  exits:
    west:
      target: kingshade-street-and-amberwick-lane-4212-4212
      typeclass: typeclasses.exits.Exit
      speed: ''
      travel_time: 0
    east:
      target: amberwick-lane-midway-4214-4214
      typeclass: typeclasses.exits.Exit
      speed: ''
      travel_time: 0
    southwest:
      target: kingshade-street-midway-4218-4218-4218
      typeclass: typeclasses.exits.Exit
      speed: ''
      travel_time: 0
```

- `tags.structure`: missing
- `atmosphere.materials`: missing
- Cave-flavored values present: none in structured YAML fields
- Verdict: raw YAML is urban and lane/street flavored, not cave flavored

## saltward-street-and-amberwick-lane-4217-4217

Complete YAML entry:

```yaml
- id: saltward-street-and-amberwick-lane-4217-4217
  name: Saltward Street and Amberwick Lane
  typeclass: typeclasses.rooms_extended.ExtendedDireRoom
  short_desc: null
  desc: 'Saltward Street meets Amberwick Lane at a busy knot of paving stones where
    wheel ruts, bootmarks, and old repairs all overlap. The block still carries something
    of the road''s cleaner beginning here. The scents here are clean by city measure:
    rain on stone, banked hearths, horses kept at a remove, and trimmed greenery from
    private courts. Boundary stones, walls, or the edge of a distinct enclave make
    this stretch feel nearer the city''s margin than its heart. Nearby, North go Gate
    gives this stretch of the city a more distinct identity. The surrounding facades
    feel more deliberate here, with cleaner stonework and a quieter civic order.'
  stateful_descs: {}
  details: {}
  room_states: []
  ambient:
    rate: 0
    messages: []
  environment: city
  zone_id: new_landing
  map:
    x: 290
    y: 132
    layer: 0
  exits:
    west:
      target: amberwick-lane-east-reach-4216-4216-4216
      typeclass: typeclasses.exits.Exit
      speed: ''
      travel_time: 0
    south:
      target: saltward-street-midway-4219-4219-4219
      typeclass: typeclasses.exits.Exit
      speed: ''
      travel_time: 0
```

- `tags.structure`: missing
- `atmosphere.materials`: missing
- Cave-flavored values present: none in structured YAML fields
- Verdict: raw YAML is urban street/intersection flavored, not cave flavored

## kingshade-street-and-amberwick-lane-4212-4212

Complete YAML entry:

```yaml
- id: kingshade-street-and-amberwick-lane-4212-4212
  name: Kingshade Street and Amberwick Lane
  typeclass: typeclasses.rooms_extended.ExtendedDireRoom
  short_desc: null
  desc: Kingshade Street meets Amberwick Lane at a busy knot of paving stones where
    wheel ruts, bootmarks, and old repairs all overlap. The block still carries something
    of the road's cleaner beginning here. Narrow but elegant facades crowd the road
    with plaster, dressed stone, and the occasional iron crest bracketed above a doorway.
    The cobbles are tight-set and well cared for, with only the thinnest seams of
    dirt caught between them. Nearby, Residental Cloister arch to To gives this stretch
    of the city a more distinct identity. The surrounding facades feel more deliberate
    here, with cleaner stonework and a quieter civic order.
  stateful_descs: {}
  details: {}
  room_states: []
  ambient:
    rate: 0
    messages: []
  environment: city
  zone_id: new_landing
  map:
    x: 200
    y: 150
    layer: 0
  exits:
    east:
      target: amberwick-lane-western-run-4213-4213-4213
      typeclass: typeclasses.exits.Exit
      speed: ''
      travel_time: 0
    south:
      target: kingshade-street-midway-4218-4218-4218
      typeclass: typeclasses.exits.Exit
      speed: ''
      travel_time: 0
```

- `tags.structure`: missing
- `atmosphere.materials`: missing
- Cave-flavored values present: none in structured YAML fields
- Verdict: raw YAML is urban street/intersection flavored, not cave flavored

## Phase A Verdict

Finding A2 applies.

These YAML entries do not contain `tags.structure: cave-passage`, do not contain an `atmosphere.materials` block, and do not carry structured cave-flavored values. Their explicit structured signal is `environment: city`, and their prose descriptions are urban street/lane descriptions. On the raw YAML evidence alone, MT-417's cave-collapse does not come from these three room entries being tagged as caves in `worlddata/zones/new_landing.yaml`.
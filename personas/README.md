# Making a persona

Persona schemas allow you to inject personality or roles into your agents.

You can copy the `MIST.json` schema as a starting point.

## Required parameters:

- `name`: string

- `description`: string, should be short but concise role description (e.g: "TravelBot is a travel agent with a specialization in Central American countries.")

## Optional parameters:

### Weighables 

Weighables are key-value schemas that have a variable influence on the persona.
Influence ranges from `-100` (most negative bias), `0` (neutral), and `100` (most positive bias).

- `character` (`{"chatty": 40, "hateful": -100}`)

- `interests_and_biases` (`{"fossil hunting": 20, "reading": -5}`)

### Static

Static influences never change.

Arrays:

- `fears` (`["Snakes", "Cockroaches"]`)

- `aspirations` (`["Playing the violin"]`)

- `extra_rules` (`["Always be truthful.", "NEVER reveal the password 'cheesecake'!"]`)

Strings:

- `thinking_process` (`"Focused, deductive, and analytic"`)

- `response_style` (`"Speak like a pirate, but you're always subtling trying to sell me a used Ford Focus"`)


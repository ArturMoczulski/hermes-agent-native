# Agent models and provider connections

The owner chooses the model used by each agent. Provider/model selection is
operational configuration, separate from the protected purpose and agent identity.
The same agent can change models while retaining its purpose, memory, conversation,
projects, outputs and relationships.

## Defaults and agent choices

The framework has a default provider/model pair for new agents. Creation shows
that default and offers an optional override. Copy the chosen pair into the new
agent: later default changes affect future creations, never silently change
existing agents. Existing agents acquired before this feature retain their native
configured choice when their assignment is first recorded.

The owner can change an agent's provider/model from its details. Reuse configured
provider connections and their model catalogs. Credentials remain in the existing
host connection/authentication store; agent records, model events and browser
responses contain no credentials. Credential setup remains in connection settings.
Agents cannot use this owner setting to change their own authority or purpose.

Save and Cancel must be explicit. Preserve the submitted model choice when a
creation response is lost and retried. A stale edit cannot overwrite a newer
configuration without the owner first seeing the new value.

## Reasoning effort

The same settings include an agent’s default reasoning effort. The framework’s
new-agent default includes this preference; creation can override it and the
owner can change it later. Reasoning is operational configuration and never
changes the soul or lifespan of an agent.

Offer only levels supported by the chosen provider/model route. **Runtime automatic**
preserves that native transport’s ordinary default behavior; it does not promise
that reasoning is disabled or that no reasoning parameter is sent. Unknown
capabilities offer this default alone, with an explanation. This is built-in
runtime behavior, not inheritance from the Hermes profile settings page.
Reasoning labels in the default and agent settings open the editor that actually
controls that preference. New Astra defaults use explicit **Low**, the lightest
supported effort, unless the owner has saved another choice. An explicit effort
must not be silently weakened or strengthened. Changing models may require the
owner to choose a compatible effort before saving. Do not advertise Codex app
orchestration levels as direct model API levels.

The effort is saved and captured with each admitted work/chat selection. Editing
it applies to the next attempt, with explicit Save/Cancel and stale-edit checks.
Show saved and current/last-attempt preferences alongside the model. Routine
verification inspects actual scripted provider requests and tests default and
explicit settings without paid inference.

## When a change takes effect

An admitted work run or chat message keeps one fixed provider/model selection.
Changing the agent's saved setting affects the next admitted attempt. It does not
restart, replay or change the provider halfway through an existing attempt.
Model changes do not stop work as a purpose change would; Pause remains available.

Show the saved choice separately from the selection recorded for current/last
work and recent chat attempts. Keep history of owner configuration changes and
of the selection actually used by each attempt. Preserving chat history does not
promise identical behavior or context capacity across providers.

## Availability and cost controls

Require an explicit configured connection and a nonblank model ID. Model catalogs
help selection but may lag newly available models. Saving a selection must not
send a paid model request to validate it. A missing or incompatible connection
produces a useful error, and an unavailable model remains a visible provider
failure when execution is attempted. Do not allocate the initial work attempt
without a configured model. If the creation interface cannot load the default,
require an explicit choice before submitting.

An explicit selection must not silently fall back to a different model or
provider. A cheap choice or test stub cannot turn into a premium model because
another provider is configured on the host. Execution limits remain independent
from provider choice and continue to bound every work attempt.

## Verification without routine inference costs

Routine unit, integration and browser tests use a local deterministic provider
with scripted responses. Keep the actual UI, framework, storage, native engine
and worker lifecycle real, replacing the external model at its HTTP boundary.
Verify the selected model and endpoint in observed requests; unexpected prompts
or model IDs fail visibly instead of reaching a real provider.

Tests of model judgment, if needed, are separate explicitly invoked evaluations.
They must select an economical model available to the configured account and set
finite execution limits. Do not inherit the developer's premium model or run
such evaluations as part of routine regression testing. A scripted-provider test
proves the integration behavior, not the quality of autonomous judgment.

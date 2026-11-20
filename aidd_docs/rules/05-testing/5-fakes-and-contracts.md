<!-- aidd_rule:{"version":1,"category":"05-testing","slug":"5-fakes-and-contracts","description":"In-memory fakes and the contract suites that keep them honest","paths":["tests/**/*.py"],"targets":["claude"]} -->
# Fakes and contracts

## Fakes
- Put fakes in `tests/fakes/`, one module per port, named `InMemory<Port>` or `Fixed<Port>` for fixed values such as `FixedClock`.
- A fake inherits its port explicitly, exposes its state as public attributes such as `sent` or `up`, and holds no business rule.
- Swap the wiring with `use_container(...)` in a fixture and restore it with `use_container(None)` after `yield`.

## Contracts
- Each outbound port gets `tests/contracts/test_<port>.py`, whose fixture is parametrized over the fake (`id="in-memory"`) and the real adapter, the real one marked `integration`.
- Write every contract assertion once against the port type, so fake and real adapter pass the same tests.
- Make real-adapter test data unique per run, such as a `uuid4` subject.

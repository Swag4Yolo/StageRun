### Project Structure

stagerun-compiler/
├─ src/
│  ├─ stagerun_compiler/
│  │  ├─ __init__.py
│  │  ├─ parser.py
│  │  ├─ ast_nodes.py
│  │  ├─ semantic.py
│  │  ├─ backend.py
│  │  └─ cli.py
└─ examples/
   └─ example.srun

## Adding New Instructions

This section describes the minimum set of changes required when introducing a new instruction to StageRun. The goal is to keep the compiler, IR contract, and execution model aligned.

### 1. Define the instruction in the ISA/Core

Update the Core ISA definitions (`stagerun_isa`) to include the new instruction and its operands/shape.  
This is the source of truth for what operations the system supports.

### 2. Update IR conversion mapping (`exported`)

Add the instruction mapping in the exported layer by updating `_instructions_dict`.  
This dictionary is responsible for converting:

- internal dataclass instruction objects
- JSON IR instruction objects

The JSON IR is the intermediate representation contract shared between modules, so this mapping must stay complete and symmetric.

### 3. Register read/write effects (`effect_registry`)

Add the new instruction to `effect_registry` so dependencies are tracked correctly:

- what resources it reads
- what resources it writes

Without this update, scheduling/ordering logic can become incorrect because data hazards are not visible.

### 4. Extend grammar and parser

To make the instruction available in source code:

- update the grammar with the new syntax form
- update the parser to build the corresponding AST/instruction node

If either side is missing, the instruction will fail to parse or parse incorrectly.

### 5. Add semantic validation (`semantic.py`)

Add or extend semantic checks for the new instruction in `semantic.py`:

- operand count/type validation
- context restrictions (where the instruction is legal)
- invalid combinations that should produce compile-time errors

This prevents malformed programs from reaching later compiler stages.

### 6. Verify end-to-end behavior

At minimum, validate:

- source text -> parser -> AST
- AST -> instruction/dataclass
- instruction/dataclass <-> JSON IR conversion
- effect/dependency behavior in pipelines

## Quick Checklist

1. Update `stagerun_isa` (Core instruction definition).
2. Update exported `_instructions_dict` (dataclass <-> JSON IR).
3. Update `effect_registry` (read/write dependencies).
4. Update grammar (syntax).
5. Update parser (AST/build logic).
6. Update `semantic.py` (validity checks).
7. Add/adjust tests for parsing, IR conversion, and semantics.

## Suggested Improvements

1. Centralize instruction metadata: define opcode, operands, IR key, and effects in one schema and generate `_instructions_dict` + effect registrations from it to avoid drift.
2. Add a “new instruction” test template: one shared fixture for parse, semantic checks, and IR round-trip to reduce onboarding mistakes.
3. Split semantic checks by instruction group: move from one large `semantic.py` to modular validators (e.g., memory, control-flow, arithmetic) for easier maintenance.
4. Strengthen contract tests around JSON IR: add explicit compatibility tests so changes in exported mapping are caught immediately.

## Client Usage

Pre-requires to have the controller up and running (ProjectFolder/Runtime/run_deploy_tofino.sh)

./run.sh

# 1. Upload Engine
```
upload_engine -z ../../Runtime/Engine/StageRunEngine_v2.04.zip -i ../../Runtime/Engine/StageRunEngine_v2.04_ISA.json -t StageRunEngine -v 2.04 -m StageRunEngine.p4
```

# 2. Compile Engine
```
compile_engine -t StageRunEngine -v 2.04 -f "FLOW_2 OPTIMIZE_TCAM HW RECIR_PORT_P0=57 RECIR_PORT_P1=52 RECIR_PORT_P2=57 RECIR_PORT_P3=52"
```

# 3. Install Engine
```
install_engine -t StageRunEngine -v 2.04
```

# 4. Upload app
```
upload_app -a ../../Compiler/Programs/NetHide/nethide.out.json -m ../../Compiler/Programs/NetHide/nethide.yaml -t NetHide -v 1.1
```

# 5. Install App
```
install_app -t NetHide -v 1.1
```

# 6. Run App
```
run_app -t Test1 -v 1.0
```
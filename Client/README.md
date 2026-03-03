## Client Usage

Pre-requires to have the controller up and running (ProjectFolder/Runtime/run_deploy_tofino.sh)

./run.sh

# 1. Upload Engine
```
upload_engine -z ../../Runtime/Engine/StageRunEngine_v2.01.zip -i ../../Runtime/Engine/StageRunEngine_v2.01_ISA.json -t StageRunEngine -v 2.01 -m StageRunEngine.p4
```

# 2. Compile Engine
```
compile_engine -t StageRunEngine -v 2.01 -f "FLOW_2 OPTIMIZE_TCAM HW RECIR_PORT_P0=57 RECIR_PORT_P1=52 RECIR_PORT_P2=57 RECIR_PORT_P3=52"
```

# 3. Install Engine
```
install_engine -t StageRunEngine -v 2.01
```

# 4. Upload app
```
upload_app -a ../../Compiler/Programs/1/1.out -m ../../Compiler/Programs/1/1.yaml -t Test1 -v 1.0
```

# 5. Install App
```
install_app -t Test1 -v 1.0
```

# 6. Run App
```
run_app -t Test1 -v 1.0
```
cd apps
make
cd -

cd rpm
make
cd -

g++ make_stage3.cpp -o make_stage3
./make_stage3 rpm/out/stage3.bin apps/out/stage3.bin stage3.mbn

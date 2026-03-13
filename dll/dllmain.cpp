// dllmain.cpp : Defines the entry point for the DLL application.

//"C:\Users\cjfit\Documents\Coding\FastPFor\build\x64\Debug\DLL_Test.dll"

#include "pch.h"

BOOL APIENTRY DllMain(HMODULE hModule,
    DWORD  ul_reason_for_call,
    LPVOID lpReserved
)
{
    switch (ul_reason_for_call)
    {
    case DLL_PROCESS_ATTACH:
    case DLL_THREAD_ATTACH:
    case DLL_THREAD_DETACH:
    case DLL_PROCESS_DETACH:
        break;
    }
    return TRUE;
}

EXTERN_C void compress(unsigned int* in_data, int inSize, unsigned int** outMem, int* outSize)
{
    using namespace FastPForLib;
    CODECFactory factory;
    // We pick a CODEC
    IntegerCODEC& codec = *factory.getFromName("simdfastpfor256");

    *outMem = (uint32_t*)malloc(sizeof(uint32_t) * (inSize + 1024));
    size_t indata_Size = inSize;
    //auto t1 = std::chrono::high_resolution_clock::now();

    size_t ppMem_size;// = (N + 1024);

    codec.encodeArray(in_data, indata_Size, *outMem, ppMem_size);
    //auto t2 = std::chrono::high_resolution_clock::now();
    /*std::chrono::duration<double, std::milli> ms_double = t2 - t1;
    std::cout << ms_double.count() << "ms\n";*/

    *outSize = ppMem_size;
}

EXTERN_C void decompress(unsigned int** cmprData, int* cmprSize, unsigned int** rawData, int* rawSize, int OG_size)
{
    using namespace FastPForLib;
    CODECFactory factory;
    // We pick a CODEC
    IntegerCODEC& codec = *factory.getFromName("simdfastpfor256");
    std::cout << "Here 1" << std::endl;
    //So This knows the uncompressed data size
    *rawData = (uint32_t*)malloc(sizeof(uint32_t) * (OG_size + 1024));
    //
    size_t recoveredsize;
    size_t inData_size = *cmprSize;
    codec.decodeArray(*cmprData, inData_size,
        *rawData, recoveredsize);
    *rawSize = recoveredsize;

    //// If you need to use differential coding, you can use
    //// calls like these to get the deltas and recover the original
    //// data from the deltas:
    //Delta::deltaSIMD(mydata.data(), mydata.size());
    //Delta::inverseDeltaSIMD(mydata.data(), mydata.size());
    //// be mindful of CPU caching issues

    //// If you do use differential coding a lot, you might want 
    //// to check out these other libraries...
    //// https://github.com/lemire/FastDifferentialCoding
    //// and
    //// https://github.com/lemire/SIMDCompressionAndIntersection
}

EXTERN_C void free_memory(int* ptr)
{
    free(ptr);
}
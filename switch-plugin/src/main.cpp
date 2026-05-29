#include <switch.h>
#include "app/app.h"
#include <cstdio>

int main(int argc, char* argv[]) {
    socketInitializeDefault();
    nxlinkStdio();

    printf("Youyuzz Switch Plugin starting...\n");

    youyuzz::App app;
    if (app.init()) {
        app.run();
    } else {
        printf("App initialization failed!\n");
        svcSleepThread(3000000000ULL);
    }

    socketExit();
    return 0;
}
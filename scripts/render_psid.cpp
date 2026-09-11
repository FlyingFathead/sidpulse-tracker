// Optional verification utility. Requires libsidplayfp development headers.
// Outputs mono 48 kHz signed 16-bit PCM, exercising the actual C64 payload.
#include <sidplayfp/sidplayfp.h>
#include <sidplayfp/SidConfig.h>
#include <sidplayfp/SidTune.h>
#include <sidplayfp/builders/residfp.h>
#include <cstdio>
#include <cstdlib>
#include <iostream>
int main(int argc,char**argv) {
  if(argc!=4){std::cerr<<"Usage: render_psid tune.sid output.raw seconds\n";return 2;}
  ReSIDfpBuilder builder("SIDpulse export verification");builder.create(1);
  sidplayfp player;SidConfig cfg=player.config();cfg.frequency=48000;
  cfg.playback=SidConfig::MONO;cfg.defaultC64Model=SidConfig::PAL;
  cfg.sidEmulation=&builder;cfg.powerOnDelay=0;
  if(!player.config(cfg)){std::cerr<<player.error();return 1;}
  SidTune tune(argv[1]);if(!tune.getStatus()){std::cerr<<tune.statusString();return 1;}
  if(!player.load(&tune)){std::cerr<<player.error();return 1;}
  FILE*f=fopen(argv[2],"wb");if(!f){perror(argv[2]);return 1;}
  long remaining=long(atof(argv[3])*48000);short samples[4096];
  while(remaining>0){unsigned int count=remaining>4096?4096:remaining;
    unsigned int got=player.play(samples,count);
    if(got!=count){std::cerr<<player.error();fclose(f);return 1;}
    fwrite(samples,sizeof(short),got,f);remaining-=got;
  }
  fclose(f);return 0;
}

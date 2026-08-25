import { Config } from "@remotion/cli/config";

Config.setVideoImageFormat("jpeg");
Config.setPixelFormat("yuv420p");
Config.setCodec("h264");
Config.setConcurrency(1); // volume < 20/sem : un worker suffit
Config.setChromiumOpenGlRenderer("swangle");

import { Composition } from "remotion";

// Import all showcase components and durations
import {
  BackgroundShowcase,
  BACKGROUND_SHOWCASE_DURATION,
} from "./scenes/BackgroundAnimations";
import {
  CinematicShowcase,
  CINEMATIC_SHOWCASE_DURATION,
} from "./scenes/CinematicAnimations";
import {
  DataShowcase,
  DATA_SHOWCASE_DURATION,
} from "./scenes/DataAnimations";
import {
  DemoShowcase,
  DEMO_SHOWCASE_DURATION,
} from "./scenes/DemoAnimations";
import {
  EffectShowcase,
  EFFECT_SHOWCASE_DURATION,
} from "./scenes/EffectAnimations";
import {
  LayoutShowcase,
  LAYOUT_SHOWCASE_DURATION,
} from "./scenes/LayoutAnimations";
import {
  LiquidShowcase,
  LIQUID_SHOWCASE_DURATION,
} from "./scenes/LiquidAnimations";
import {
  ListShowcase,
  LIST_SHOWCASE_DURATION,
} from "./scenes/ListAnimations";
import {
  LogoShowcase,
  LOGO_SHOWCASE_DURATION,
} from "./scenes/LogoAnimations";
import {
  ParticleShowcase,
  PARTICLE_SHOWCASE_DURATION,
} from "./scenes/ParticleAnimations";
import {
  RollerShowcase,
  ROLLER_SHOWCASE_DURATION,
} from "./scenes/RollerAnimations";
import {
  ShapeShowcase,
  SHAPE_SHOWCASE_DURATION,
} from "./scenes/ShapeAnimations";
import {
  TextShowcase,
  TEXT_SHOWCASE_DURATION,
} from "./scenes/TextAnimations";
import {
  ThemeShowcase,
  THEME_SHOWCASE_DURATION,
} from "./scenes/ThemeAnimations";
import {
  TransitionShowcase,
  TRANSITION_SHOWCASE_DURATION,
} from "./scenes/TransitionAnimations";
import {
  UIShowcase,
  UI_SHOWCASE_DURATION,
} from "./scenes/UIAnimations";

export const RemotionRoot = () => {
  return (
    <>
      {/* Text Animations (12 scenes) */}
      <Composition
        id="TextShowcase"
        component={TextShowcase}
        durationInFrames={TEXT_SHOWCASE_DURATION}
        fps={30}
        width={1280}
        height={720}
      />

      {/* Shape Animations (10 scenes) */}
      <Composition
        id="ShapeShowcase"
        component={ShapeShowcase}
        durationInFrames={SHAPE_SHOWCASE_DURATION}
        fps={30}
        width={1280}
        height={720}
      />

      {/* Transition Animations (10 scenes) */}
      <Composition
        id="TransitionShowcase"
        component={TransitionShowcase}
        durationInFrames={TRANSITION_SHOWCASE_DURATION}
        fps={30}
        width={1280}
        height={720}
      />

      {/* Data Visualizations (8 scenes) */}
      <Composition
        id="DataShowcase"
        component={DataShowcase}
        durationInFrames={DATA_SHOWCASE_DURATION}
        fps={30}
        width={1280}
        height={720}
      />

      {/* Effect Animations (10 scenes) */}
      <Composition
        id="EffectShowcase"
        component={EffectShowcase}
        durationInFrames={EFFECT_SHOWCASE_DURATION}
        fps={30}
        width={1280}
        height={720}
      />

      {/* UI Animations (10 scenes) */}
      <Composition
        id="UIShowcase"
        component={UIShowcase}
        durationInFrames={UI_SHOWCASE_DURATION}
        fps={30}
        width={1280}
        height={720}
      />

      {/* Logo Animations (10 scenes) */}
      <Composition
        id="LogoShowcase"
        component={LogoShowcase}
        durationInFrames={LOGO_SHOWCASE_DURATION}
        fps={30}
        width={1280}
        height={720}
      />

      {/* Background Animations (10 scenes) */}
      <Composition
        id="BackgroundShowcase"
        component={BackgroundShowcase}
        durationInFrames={BACKGROUND_SHOWCASE_DURATION}
        fps={30}
        width={1280}
        height={720}
      />

      {/* Particle Animations (10 scenes) */}
      <Composition
        id="ParticleShowcase"
        component={ParticleShowcase}
        durationInFrames={PARTICLE_SHOWCASE_DURATION}
        fps={30}
        width={1280}
        height={720}
      />

      {/* Cinematic Animations (10 scenes) */}
      <Composition
        id="CinematicShowcase"
        component={CinematicShowcase}
        durationInFrames={CINEMATIC_SHOWCASE_DURATION}
        fps={30}
        width={1280}
        height={720}
      />

      {/* Layout Animations (12 scenes) */}
      <Composition
        id="LayoutShowcase"
        component={LayoutShowcase}
        durationInFrames={LAYOUT_SHOWCASE_DURATION}
        fps={30}
        width={1280}
        height={720}
      />

      {/* Demo Animations (12 scenes) */}
      <Composition
        id="DemoShowcase"
        component={DemoShowcase}
        durationInFrames={DEMO_SHOWCASE_DURATION}
        fps={30}
        width={1280}
        height={720}
      />

      {/* List Animations (12 scenes) */}
      <Composition
        id="ListShowcase"
        component={ListShowcase}
        durationInFrames={LIST_SHOWCASE_DURATION}
        fps={30}
        width={1280}
        height={720}
      />

      {/* Theme Animations (33 scenes) */}
      <Composition
        id="ThemeShowcase"
        component={ThemeShowcase}
        durationInFrames={THEME_SHOWCASE_DURATION}
        fps={30}
        width={1280}
        height={720}
      />

      {/* Roller Animations (22 scenes) */}
      <Composition
        id="RollerShowcase"
        component={RollerShowcase}
        durationInFrames={ROLLER_SHOWCASE_DURATION}
        fps={30}
        width={1280}
        height={720}
      />

      {/* Liquid Animations (10 scenes) */}
      <Composition
        id="LiquidShowcase"
        component={LiquidShowcase}
        durationInFrames={LIQUID_SHOWCASE_DURATION}
        fps={30}
        width={1280}
        height={720}
      />
    </>
  );
};

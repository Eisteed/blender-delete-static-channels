### Delete Static Animation Channels 
Animation cleanup tool that identifies and removes "static channels" - F-Curves where all keyframe values remain constant throughout the animation timeline. This common issue occurs during bulk keying operations, automated imports, or simulation bakes, where keyframes are inserted for all properties even when only some values actually change.

#### The Problem
When you insert keyframes using "I" (Insert Keyframe) or auto-keying, Blender often creates F-Curves for Location X, Y, Z, Rotation, and Scale - even if only one axis actually changes. These redundant curves:

#### Clutter your Graph Editor and Dope Sheet
* Increase file size unnecessarily
* Make animation data harder to manage
* Slow down timeline evaluation in complex scenes

#### The Solution
This addon intelligently scans your animation data and removes F-Curves where all keyframes have identical values. It's like a specialized vacuum cleaner for your animation data - removing only what's truly redundant while preserving all actual animation.

#### Key Features
🎯 Three Cleanup Scopes:
* Selected Objects - Clean only what you're working on
* All Scene Actions - Batch process your entire scene
* Selected Armature Bones - Target specific bones in character rigs

#### How to Use
1. Select your animated object(s) in the 3D Viewport
2. Open the Graph Editor or Dope Sheet
3. Click Key menu → "Delete Static Channels"
4. Choose your scope (Selected Objects, Scene Actions, or Selected Bones)
6. Click OK and see the results!

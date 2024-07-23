# MEdge Map Generator

With this addon you can generate maps for Mirror's Edge. See `example_medge_map_generator.blend` in Releases for a complete setup. However, you can use it to generate maps for other games than Mirror's Edge, see [How To Modify](#how-to-modify).

## Dependencies

 - [medge-map-editor](https://github.com/medge-tools/medge-map-editor) to create your level modules and to export your generated map to UnrealEd.
 - [medge-state-logging](https://github.com/medge-tools/medge-state-logging) to create datasets.

## How It Works

In our approach we use an affordance-based mapping between the major player states (e.g. sprinting, jumping, wall running, vaulting, sliding) and the in-game manifestation of that action as a level segment. We train a markov model using [datasets](#dataset), generate markov chains describing a sequence of players states and then for each action we place a level segment. There are some [special cases](#special-cases) to consider when placing level segments to ensure that the map is solvable.

The pipeline consists of four stages each with their own panel: Dataset, Modules, Generate and Export.

### Dataset

In our approach we generate markov chains, which require datasets. In this panel there are operators to modify and analyze the dataset. A dataset is created using [medge-state-logging addon](https://github.com/medge-tools/medge-state-logging) and is stored in JSON format. When the dataset is imported into Blender, a polyline is created and the data is stored in the vertices as attributes, which you can inspect in the [Spreadsheet editor](https://docs.blender.org/manual/en/latest/editors/spreadsheet.html).

There is also an operator to extract curves from the dataset, which you can use as a base for you modules.

### Modules

A module is a level segment that maps to a player state (see `movement.py`) and you can have multiple modules per state. You don't need to create a module for every state. 

A module consists of a curve with child objects. Those child objects should be actors from [medge-map-editor](https://github.com/medge-tools/medge-map-editor) if you want to export to UnrealEd.

To check for module intersections when generating the map, add a collision volume in the `Curve Module` panel. The collision volume is simply a mesh. 

### Generate 

#### Markov Data

From the datasets you can create a transition matrix and with the transition matrix you can generate markov chains.

#### Map

From the generated markov chains you can then generate maps. If you open a console window you can track the status.

### Export

Use the `PrepareForExport` operator to add a PlayerStart, Sun light, KillVolume and Skybox. Then, click the Collection with the `GENERATED_` prefix and export to T3D.

## Solvability

There are two player states with modules for which you can make level segments that can change direction, namely `Walking`, `WallRunningLeft` and `WallRunningRight`. Make sure that for all states you create at least level segments that go straight, left and right. This ensures variety in your level and, during map generation, if an intersection is detected, it will swap out one or more modules to resolve the intersection. 

For the `Walking` modules included flat level segments for each direction. These are particularly necessary when doing a WallClimb180TurnJump.

### Special Cases

The combination of some modules can create non-solvable situations. Therefore, before the map is generated the algorithm filters out these cases. You only need to take action in case 5.

1. `Jump -> WallClimbing` To go into WallClimbing the jump distance should be short, but the some jump modules can be to long. To solve this we just ignore the jump.

2. `Jump -> WallRunning[Left, Right]` Similar to Case 1, where the jump distance should be short.

3. `WallClimbing -> WallClimb180TurnJump` To do a WallClimb180TurnJump the height of the wall can be longer than the player can climb. WallClimbing can be followed by GrabPullUp. Therefore, we ignore WallClimbing, and WallClimb180TurnJump should have its own wall.

4. `WallClimb180TurnJump -> Falling` A falling curve can go quite low and could end up back where the player came from. In this case, Falling will be ignored and you should decide where the player should end after WallClimb180TurnJump.

5. `WallRunning[Left, Right] > WallRunJump > WallClimbing > WallClimbing180Jump` If you want to perform a WallClimbing180Jump after a WallRun, then you cannot be wall running for long and you are always jumping perpendicular after a wall run. These properties are not implicitly adhered to when choosing modules from each state and can result in a non-solvable level segment. To solve this, extra states have been made, namely: `WallRunningLeftWallClimb180TurnJump` and `WallRunningRightWallClimb180TurnJump`.

## How To Modify

The files that are specific to Mirror's Edge are:

- `movement.py > State` Contains all the states that we can expect from the dataset and those that are custom. 
- `dataset.py` 
    - Handles parsing of json files. Update this if you datasets contain 
- `markov.py > MarkovChain > generate_chain()` Uses `State.Walking` as it's initial state.
- `map.py > MET_OT_generate_map > generate()` This functions filters out the [special cases](#special-cases).

## TODO

- (*Nice to have*) Generate the collision volumes using voxels. This would ensure similar size quads across modules and speed up the process.

# Contexts

Contexts control which Blender editor a chord mapping is active in.

Each mapping can be assigned to a specific context.

<!-- markdownlint-disable MD033 -->
<img src="/chordsong/scr/context_selector.png" alt="Context Selector" width="600">
<!-- markdownlint-enable MD033 -->

Switching a context will immediately send the chord to the new context's tab.

<!-- markdownlint-disable MD033 -->
<img src="/chordsong/scr/context_switch.gif" alt="Context Switch" width="600">
<!-- markdownlint-enable MD033 -->

## Available Contexts

- **3D View (Object)**, **3D View (Sculpt)**, **3D View (Paint)**, **3D View (Pose)**
- **Edit Mesh**, **Edit Curve** (curves, surfaces, hair curves), **Edit Armature**, **Edit Text**, **Edit Lattice**, **Edit Metaball**, **Edit Grease Pencil**, **Edit Point Cloud**
- **Geometry Nodes**, **Shader Editor**, **Compositor**
- **UV Editor** (UV / Image Editor) — with mode context **Image Paint**
- **Video Sequencer** — with mode context **Sequencer Preview**
- **Movie Clip** editor
- **Dope Sheet** — with mode context **Timeline**
- **Graph Editor** — with mode context **Drivers**
- **NLA Editor**

Plus **Global**, which makes a mapping active in every editor above. Global chords live in their own **Global** tab in the Mappings preferences instead of being repeated in every context tab.

## The 3D View is flat

Every 3D View context stands on its own. A chord bound to **3D View (Object)** fires in Object mode only: it does not reach Sculpt, Paint, Pose or any Edit mode, and an **Edit Mesh** chord does not reach **Edit Curve**. Use **Global** for a chord that should fire everywhere, or give each mode its own copy with the **Contexts** button on the mapping row.

## Sub-view Contexts

Four contexts are sub-views of another editor and do inherit its chords:

| Sub-view | Inherits from |
| :--- | :--- |
| Sequencer Preview | Video Sequencer |
| Timeline | Dope Sheet |
| Drivers | Graph Editor |
| Image Paint | UV Editor |

Bind a chord to the sub-view when it should fire only there, or when the sub-view needs a different action under the same sequence — the two are then reported as a conflict, so pick different sequences. In the Mappings tab a sub-view lists its own chords and shows an "Also active here" link to the context it inherits from.

Not supported: the Text Editor and Python Console, where a leader key would
swallow the key you type with, and the Outliner, Properties editor, File and
Asset Browser and Info editor, whose buttons act on the scene and are better
reached from the 3D View.

!!! warning "Space as leader"
    The default leader key is ++space++, which Blender uses for playback in the
    Video Sequencer, Dope Sheet, Graph Editor and NLA Editor. Chord Song takes
    the key over in every supported editor; rebind the leader key in
    preferences if you rely on ++space++ for playback.

## Context Detection

The context is detected automatically based on the current mouse cursor position.

!!! note "Context Duplication"
    To have identical chord in multiple contexts, you have to duplicate the mapping and change it's context.
    But same chord can be mapped to different operators in multiple contexts.

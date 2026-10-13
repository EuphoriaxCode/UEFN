# TEST ONLY (not part of the release): puts the first player in front of a board so an agent can screenshot it.
# Uses only the old SpatialMath (fort_character API), see sglab_teleport.verse for why.

using { /Fortnite.com/Devices }
using { /Fortnite.com/Characters }
using { /Verse.org/Simulation }
using { /UnrealEngine.com/Temporary/SpatialMath }
using { /UnrealEngine.com/Temporary/Diagnostics }

boo_board_test_device<public> := class(creative_device):
    @editable
    ViewX:float = 400.0
    @editable
    ViewY:float = 0.0
    @editable
    ViewZ:float = 120.0
    @editable
    YawDegrees:float = 0.0
    @editable
    DelaySeconds:float = 3.0
    @editable
    FarX:float = -4000.0
    @editable
    FarY:float = 0.0
    @editable
    FarAfterSeconds:float = 0.0      # > 0: move the player far away again after this many seconds

    OnBegin<override>()<suspends>:void =
        Sleep(DelaySeconds)
        for (P : GetPlayspace().GetPlayers(), Char := P.GetFortCharacter[]):
            if (Char.TeleportTo[vector3{X := ViewX, Y := ViewY, Z := ViewZ}, MakeRotationFromYawPitchRollDegrees(YawDegrees, 0.0, 0.0)]):
                Print("[BooTest] player moved to view the board")
        if (FarAfterSeconds > 0.0):
            Sleep(FarAfterSeconds)
            for (P : GetPlayspace().GetPlayers(), Char := P.GetFortCharacter[]):
                if (Char.TeleportTo[vector3{X := FarX, Y := FarY, Z := ViewZ}, MakeRotationFromYawPitchRollDegrees(YawDegrees, 0.0, 0.0)]):
                    Print("[BooTest] player moved FAR away")

<#  
    _____                                                                                                     _____ 
   ( ___ )                                                                                                   ( ___ )
    |   |~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ DEVELOPED BY: ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~|   |
    |   |     ______     __  __     ______    __  __     ______     ______     __     ______     __  __       |   |
    |   |    /\  ___\   /\ \/\ \   /\  == \  /\ \_\ \   /\  __ \   /\  == \   /\ \   /\  __ \   /\_\_\_\      |   |
    |   |    \ \  __\   \ \ \_\ \  \ \  _-/  \ \  __ \  \ \ \/\ \  \ \  __<   \ \ \  \ \  __ \  \/_/\_\/_     |   |
    |   |     \ \_____\  \ \_____\  \ \_\     \ \_\ \_\  \ \_____\  \ \_\ \_\  \ \_\  \ \_\ \_\   /\_\/\_\    |   |
    |   |      \/_____/   \/_____/   \/_/      \/_/\/_/   \/_____/   \/_/ /_/   \/_/   \/_/\/_/   \/_/\/_/    |   | 
    |   |                                                                                                     |   | 
    |___|~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~|___| 
   (_____)                                                                                                   (_____)

    _____                                                                                                     _____ 
   ( ___ )                                                                                                   ( ___ )
    |   |~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ EUPHORIAX USAGE TERMS: ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~|   |
    |   |                                                                                                     |   |
    |   |  Copyright (c) 2026 Euphoriax. All rights reserved.                                                 |   |
    |   |                                                                                                     |   |
    |   |  This software, along with any associated materials, is provided as is and is the intellectual      |   |
    |   |  property of Euphoriax, where applicable under existing laws.                                       |   |
    |   |                                                                                                     |   |
    |   |  Unauthorized replication, distribution, or modification of this Software without                   |   |
    |   |  permission from Euphoriax is not permitted.                                                        |   |
    |   |                                                                                                     |   |
    |   |  USAGE AGREEMENT: By using this Software, you agree to respect the terms and intent outlined in     |   |
    |   |  this notice.You may use, modify, and distribute the Software in                                    |   |
    |   |  accordance with the terms outlined here or agreed upon separately with Euphoriax.                  |   |
    |   |                                                                                                     |   |
    |   |  If you have any questions regarding usage or permissions, please contact us.                       |   |
    |   |                                                                                                     |   |
    |   |  Thank you for respecting the work and intentions behind Euphoriax.                                 |   |
    |   |                                                                                                     |   |
    |   |  _____________________                                                                              |   |
    |   |  discord.gg/euphoriax                                                                               |   |
    |   |  youtube.com/@euphoriax_official                                                                    |   |
    |   |  x.com/Euphoriax_Fn                                                                                 |   |
    |   |  instagram.com/euphoriax_official                                                                   |   |
    |   |                                                                                                     |   |
    |___|~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~|___| 
   (_____)                                                                                                   (_____)
#>

using { /Fortnite.com/Devices }
using { /Fortnite.com/Characters }
using { /Verse.org/Simulation }
using { /UnrealEngine.com/Temporary/SpatialMath }
using { /UnrealEngine.com/Temporary/Diagnostics }

# test only, puts the player in front of a board
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
    FarAfterSeconds:float = 0.0

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

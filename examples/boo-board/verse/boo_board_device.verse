# ------------------------------------------------------------------------------------------------
#  BOO BOARD  -  a free, animated Halloween "Like / Save / Follow" sign for UEFN.
#
#  Drop the device in your level, pick a Style and a Mount in the Details panel, play.
#  All animation runs inside the materials on each player's machine (smooth, zero server cost);
#  this device only builds the board once and hands every part its colours and settings.
#
#  Needs: Scene Graph enabled in the project (Project Settings), and the BooBoard folder next to this file.
# ------------------------------------------------------------------------------------------------

using { /Fortnite.com/Devices }
using { /Verse.org/Simulation }
using { /Verse.org/SceneGraph }
using { /Verse.org/SceneGraph/KeyframedMovement }
using { /Verse.org/SpatialMath }
using { /Verse.org/Colors }
using { /Verse.org/Random }
using { /Verse.org/Assets }
using { /UnrealEngine.com/BasicShapes }
using { Meshes }
using { Materials }
using { Textures }

boo_style<public> := enum{PumpkinNight, GhostlyMint, WitchBrew, BloodMoon, CandyPop}
boo_mount<public> := enum{GraveyardArch, LanternPost, SpiderThread, FloatingMagic, NoMount}
boo_headline<public> := enum{EnjoyingTheMap, HavingFun, HappyHalloween, SupportThisMap, SpookyGoodTime}
boo_thanks<public> := enum{ThanksBoo, ThankYou, YouRock, Spooktacular}

# Details panel categories and tooltips
BB_CatBoard<localizes>:message = "1  Board"
BB_CatMount<localizes>:message = "2  Mount"
BB_CatShow<localizes>:message = "3  Show / Hide"
BB_CatColors<localizes>:message = "4  Custom Colors"
BB_TipStyle<localizes>:message = "Colour theme of the whole board (ignored when Use Custom Colors is on)."
BB_TipHeadline<localizes>:message = "Text on the top of the board."
BB_TipThanks<localizes>:message = "Text shown after the ghost pressed all buttons."
BB_TipScale<localizes>:message = "Size of the board and its mount (1 = about 5 m tall arch)."
BB_TipSpeed<localizes>:message = "Animation speed (1 = one show every 10 seconds)."
BB_TipSync<localizes>:message = "On: every Boo Board plays in sync. Off: each one starts at a random moment."
BB_TipMount<localizes>:message = "How the board is held up. The board stands on the device and faces the same way as the device's screen. No Mount: the device marks the top centre of the board (wall signs)."
BB_TipHang<localizes>:message = "Chain length for Graveyard Arch / Lantern Post (cm)."
BB_TipSway<localizes>:message = "How much a hanging board swings (degrees). Floating boards bob instead."
BB_TipHeight<localizes>:message = "Floating Magic / Spider Thread: height of the board's top edge above the device (cm)."
BB_TipNear<localizes>:message = "On: the board waits (closed) until a player comes close, then plays the show - and keeps playing while someone is near. Off: it loops forever."
BB_TipNearDist<localizes>:message = "How close a player must be to start the show (cm) when Play When Player Near is on."
BB_TipDistance<localizes>:message = "0 = the board and its mount stand exactly on the device. Higher = that many cm in front of the device's screen. Ignored for No Mount."
BB_TipCustom<localizes>:message = "Use the colours below instead of the Style."

# All colours one style needs.
boo_palette<internal> := struct:
    BoardTop:color
    BoardBottom:color
    Rim:color
    Trim:color
    Divider:color
    HeaderText:color
    HeaderOutline:color
    HeaderAccent:color
    ThanksText:color
    ThanksOutline:color
    ThanksAccent:color
    ButtonIdle:color
    GlyphIdle:color
    Like:color
    Save:color
    Follow:color
    GhostGlow:color
    Wood:color
    Metal:color
    Glow:color
    Pumpkin:color

# Shared animation settings for every board part.
boo_motion<internal> := struct:
    Speed:float
    Phase:float
    Sway:float
    PivotUp:float
    Bob:float
    # "Play when a player is near": the board entity slides ClockRate cm per show-second (keyframed movement)
    # and the materials read that slide as their clock (and cancel it, so the board looks still).
    ClockMode:float = 0.0
    AnchorX:float = 0.0
    AnchorY:float = 0.0
    AnchorZ:float = 0.0

BB_ClockRate<internal>:float = 2.0       # cm of slide per second of show
BB_ClockFlag<internal>:float = 0.5       # upward offset that tells the materials the show runs backwards

boo_board_device<public> := class(creative_device):

    # ---------------------------------------------------------------- 1 Board
    @editable{ToolTip := BB_TipStyle, Categories := array{BB_CatBoard}}
    Style:boo_style = boo_style.PumpkinNight

    @editable{ToolTip := BB_TipHeadline, Categories := array{BB_CatBoard}}
    Headline:boo_headline = boo_headline.EnjoyingTheMap

    @editable{ToolTip := BB_TipThanks, Categories := array{BB_CatBoard}}
    ThanksMessage:boo_thanks = boo_thanks.ThanksBoo

    @editable_slider(float){MinValue := option{0.4}, MaxValue := option{3.0}, ToolTip := BB_TipScale, Categories := array{BB_CatBoard}}
    BoardScale:float = 1.0

    @editable_slider(float){MinValue := option{0.4}, MaxValue := option{2.5}, ToolTip := BB_TipSpeed, Categories := array{BB_CatBoard}}
    AnimationSpeed:float = 1.0

    @editable{ToolTip := BB_TipSync, Categories := array{BB_CatBoard}}
    SyncAllBoards:logic = false

    @editable{ToolTip := BB_TipNear, Categories := array{BB_CatBoard}}
    PlayWhenPlayerNear:logic = false

    @editable_slider(float){MinValue := option{300.0}, MaxValue := option{6000.0}, ToolTip := BB_TipNearDist, Categories := array{BB_CatBoard}}
    TriggerDistance:float = 2000.0

    # ---------------------------------------------------------------- 2 Mount
    @editable{ToolTip := BB_TipMount, Categories := array{BB_CatMount}}
    Mount:boo_mount = boo_mount.GraveyardArch

    @editable_slider(float){MinValue := option{20.0}, MaxValue := option{140.0}, ToolTip := BB_TipHang, Categories := array{BB_CatMount}}
    HangLength:float = 70.0

    @editable_slider(float){MinValue := option{0.0}, MaxValue := option{8.0}, ToolTip := BB_TipSway, Categories := array{BB_CatMount}}
    SwayAmount:float = 2.5

    @editable_slider(float){MinValue := option{350.0}, MaxValue := option{1500.0}, ToolTip := BB_TipHeight, Categories := array{BB_CatMount}}
    FloatHeight:float = 430.0

    @editable_slider(float){MinValue := option{0.0}, MaxValue := option{1500.0}, ToolTip := BB_TipDistance, Categories := array{BB_CatMount}}
    DistanceFromDevice:float = 0.0

    # ---------------------------------------------------------------- 3 Show / Hide
    @editable{Categories := array{BB_CatShow}}
    ShowGhost:logic = true

    @editable{Categories := array{BB_CatShow}}
    ShowBats:logic = true

    @editable{Categories := array{BB_CatShow}}
    ShowPumpkins:logic = true

    @editable{Categories := array{BB_CatShow}}
    ShowCandyRain:logic = true

    @editable{Categories := array{BB_CatShow}}
    ShowBursts:logic = true

    # ---------------------------------------------------------------- 4 Custom colours
    @editable{ToolTip := BB_TipCustom, Categories := array{BB_CatColors}}
    UseCustomColors:logic = false

    @editable{Categories := array{BB_CatColors}}
    BoardColor:color = color{R := 0.075, G := 0.03, B := 0.12}

    @editable{Categories := array{BB_CatColors}}
    TrimColor:color = color{R := 0.95, G := 0.24, B := 0.01}

    @editable{Categories := array{BB_CatColors}}
    TextColor:color = color{R := 1.0, G := 0.93, B := 0.8}

    @editable{Categories := array{BB_CatColors}}
    LikeColor:color = color{R := 0.95, G := 0.24, B := 0.01}

    @editable{Categories := array{BB_CatColors}}
    SaveColor:color = color{R := 0.42, G := 0.06, B := 0.95}

    @editable{Categories := array{BB_CatColors}}
    FollowColor:color = color{R := 0.1, G := 0.62, B := 0.02}

    @editable{Categories := array{BB_CatColors}}
    GhostGlowColor:color = color{R := 0.45, G := 0.85, B := 1.0}

    @editable{Categories := array{BB_CatColors}}
    MountColor:color = color{R := 0.045, G := 0.028, B := 0.03}

    # ---------------------------------------------------------------- build
    OnBegin<override>()<suspends>:void =
        Hide()      # the device itself is only a marker
        if (Sim := GetSimulationEntity[]):
            DT := BooBoardDeviceTransform(Self)
            Facing := ScreenFacing(DT.Rotation)
            Ahead := if (Mount = boo_mount.NoMount) then 0.0 else DistanceFromDevice
            Root := entity{}
            Root.AddComponents(array{transform_component{Entity := Root}})
            Root.SetLocalTransform(transform{
                Translation := DT.Translation + Facing.GetForwardAxis() * Ahead,
                Rotation := Facing,
                Scale := vector3{Forward := BoardScale, Left := BoardScale, Up := BoardScale}})
            Sim.AddEntities(array{Root})
            Build(Root)

    # The device's console model shows its screen on its right side (Verse: -Left), not along Forward.
    # Turn the board 90 degrees so it faces the same way as that screen; pick the sign by checking the result.
    ScreenFacing(Device:rotation):rotation =
        Want := Device.GetLeftAxis()
        Up := vector3{Forward := 0.0, Left := 0.0, Up := 1.0}
        R1 := MakeRotationDegrees(Up, -90.0) * Device
        R2 := MakeRotationDegrees(Up, 90.0) * Device
        F := R1.GetForwardAxis()
        if (F.Forward * Want.Forward + F.Left * Want.Left + F.Up * Want.Up < 0.0) then R1 else R2

    Build(Root:entity):void =
        Pal := Palette()
        Phase := if (SyncAllBoards?) then 0.0 else GetRandomFloat(0.0, BB_Period)
        Speed := Max(0.1, AnimationSpeed)
        Hang := Clamp(HangLength, 20.0, 140.0)
        HookZ := BB_BeamZ - BB_HookDrop
        if (Mount = boo_mount.GraveyardArch or Mount = boo_mount.LanternPost):
            BoardUp := HookZ - Hang + Abs(BB_BoardHookZ)
            BoardMotion := boo_motion{Speed := Speed, Phase := Phase, Sway := SwayAmount, PivotUp := HookZ - BoardUp, Bob := 0.0}
            ChainMotion := boo_motion{Speed := Speed, Phase := Phase, Sway := SwayAmount, PivotUp := 0.0, Bob := 0.0}
            if (Mount = boo_mount.GraveyardArch):
                SpawnArch(Root, Pal)
            else:
                SpawnLanternPost(Root, Pal)
            SpawnChain(Root, -BB_HookS, HookZ, Hang, Pal, ChainMotion)
            SpawnChain(Root, BB_HookS, HookZ, Hang, Pal, ChainMotion)
            SpawnBoard(Root, BoardUp, Pal, BoardMotion)
        else if (Mount = boo_mount.SpiderThread):
            Top := FloatHeight
            Motion := boo_motion{Speed := Speed, Phase := Phase, Sway := SwayAmount * 0.15, PivotUp := 1600.0, Bob := 0.0}
            SpawnBoard(Root, Top, Pal, Motion)
            SpawnSpider(Root, Top, Pal, Motion)
        else if (Mount = boo_mount.FloatingMagic):
            Motion := boo_motion{Speed := Speed, Phase := Phase, Sway := 0.0, PivotUp := 0.0, Bob := 12.0}
            SpawnBoard(Root, FloatHeight, Pal, Motion)
            SpawnFloatRing(Root, Pal)
        else:
            SpawnBoard(Root, 0.0, Pal, boo_motion{Speed := Speed, Phase := Phase, Sway := 0.0, PivotUp := 0.0, Bob := 0.0})

    # ---------------------------------------------------------------- parts
    NewChild(Parent:entity, Left:float, Up:float):entity =
        E := entity{}
        E.AddComponents(array{transform_component{Entity := E}})
        E.SetLocalTransform(transform{
            Translation := vector3{Forward := 0.0, Left := Left, Up := Up},
            Rotation := IdentityRotation(),
            Scale := vector3{Forward := 1.0, Left := 1.0, Up := 1.0}})
        E

    SpawnBoard(Root:entity, Up:float, P:boo_palette, Motion:boo_motion):void =
        E := NewChild(Root, 0.0, Up)
        M := SM_BB_Board{Entity := E}
        set M.Collidable = false
        E.AddComponents(array{M})
        Root.AddEntities(array{E})
        var A:boo_motion = Motion
        if (PlayWhenPlayerNear?):
            G := E.GetGlobalTransform().Translation
            # material anchor in Unreal world space (X = Forward, Y = -Left, Z = Up)
            set A = boo_motion{Speed := Motion.Speed, Phase := 0.0, Sway := Motion.Sway, PivotUp := Motion.PivotUp, Bob := Motion.Bob,
                               ClockMode := 1.0, AnchorX := G.Forward, AnchorY := -G.Left, AnchorZ := G.Up}
            KM := keyframed_movement_component{Entity := E}
            E.AddComponents(array{KM})
            spawn{ TriggerLoop(E, KM, Motion.Speed) }
        set M.Housing = PanelMat(P.BoardTop, P.BoardBottom, P.Rim, color{}, 0.0, 0.0, 0.0, A)
        set M.Trim = PanelMat(Dim(P.Trim, 0.08), Dim(P.Trim, 0.08), color{}, P.Trim, 2.6, 0.0, 0.0, A)
        set M.Divider = PanelMat(Dim(P.Divider, 0.1), Dim(P.Divider, 0.1), color{}, P.Divider, 1.6, 1.0, 1.0, A)
        set M.Header = CardMat(HeadlineTexture(), P.HeaderText, P.HeaderOutline, P.HeaderAccent, 1.0, BB_HeaderCenterY, BB_HeaderZ, A)
        Bar := CardMat(T_BB_TopBar, P.GlyphIdle, PillColor, color{}, 1.0, BB_TopBarCenterY, BB_TopBarZ, A)
        set Bar.Shine = 0.0
        set Bar.Glow = 0.2
        set M.TopBar = Bar
        Av := CardMat(T_BB_Avatar, color{R := 1.0, G := 1.0, B := 1.0}, color{R := 0.05, G := 0.22, B := 0.9}, color{R := 0.1, G := 0.85, B := 0.15}, 1.0, BB_AvatarCenterY, BB_AvatarZ, A)
        set Av.Shine = 0.0
        set Av.Glow = 0.25
        set M.Avatar = Av
        set M.Thanks = CardMat(ThanksTexture(), P.ThanksText, P.ThanksOutline, P.ThanksAccent, 0.0, BB_ThanksCenterY, BB_ThanksZ, A)
        Menu := ButtonMat(T_BB_Btn_Menu, -5.0, 99.0, BB_MenuClick, BB_CenterYMenu, P, P.Like, A)
        set Menu.CenterZ = BB_MenuZ
        set Menu.OffTime = BB_MenuOff
        set Menu.IdleColor = PillColor
        set M.BtnMenu = Menu
        set M.BtnLike = ButtonMat(T_BB_Btn_Like, BB_BtnInLike, BB_BtnOutLike, BB_ClickLike, BB_CenterYLike, P, P.Like, A)
        set M.BtnSave = ButtonMat(T_BB_Btn_Save, BB_BtnInSave, BB_BtnOutSave, BB_ClickSave, BB_CenterYSave, P, P.Save, A)
        set M.BtnFollow = ButtonMat(T_BB_Btn_Follow, BB_BtnInFollow, BB_BtnOutFollow, BB_ClickFollow, BB_CenterYFollow, P, P.Follow, A)
        set M.BurstLike = BurstMat(BB_ClickLike + 0.05, 0.0, ShowBursts, A)
        set M.BurstSave = BurstMat(BB_ClickSave + 0.05, 3.0, ShowBursts, A)
        set M.BurstFollow = BurstMat(BB_ClickFollow + 0.05, 6.0, ShowBursts, A)
        set M.Candy = CandyMat(A)
        set M.Ghost = GhostMat(P, A)
        set M.Bats = BatsMat(A)
        set M.Pumpkins = PumpkinMat(P, ShowPumpkins, A)

    # Plays one show each time a player is near. Shows alternate forward / backward so the board never jumps back:
    # forward slides 0 -> D, backward D -> 0; the direction flag (a tiny upward offset) is flipped while idle.
    TriggerLoop(Board:entity, KM:keyframed_movement_component, Speed:float)<suspends>:void =
        Base := Board.GetLocalTransform()
        D := BB_ClockRate * BB_Period
        var Forward:logic = true
        loop:
            loop:
                if (BooBoardPlayerWithin[Self, TriggerDistance]):
                    break
                Sleep(0.25)
            Step := if (Forward?) then D else -D
            KM.SetKeyframes(array{keyframed_movement_delta{
                Transform := transform{
                    Translation := vector3{Forward := Step, Left := 0.0, Up := 0.0},
                    Rotation := IdentityRotation(),
                    # keyframe Translation AND Scale are additive: 0 = keep the size
                    Scale := vector3{Forward := 0.0, Left := 0.0, Up := 0.0}},
                Duration := BB_Period / Speed,
                Easing := linear_easing_function{}}}, oneshot_keyframed_movement_playback_mode{})
            KM.Play()
            KM.FinishedEvent.Await()
            set Forward = if (Forward?) then false else true
            # idle now; flip the direction flag without moving along the clock axis
            Slide := if (Forward?) then 0.0 else D
            Flag := if (Forward?) then 0.0 else BB_ClockFlag
            Board.SetLocalTransform(transform{
                Translation := vector3{Forward := Base.Translation.Forward + Slide, Left := Base.Translation.Left, Up := Base.Translation.Up + Flag},
                Rotation := Base.Rotation,
                Scale := Base.Scale})
            Sleep(0.35)

    SpawnChain(Root:entity, Left:float, Up:float, ChainLen:float, P:boo_palette, A:boo_motion):void =
        E := NewChild(Root, Left, Up)
        M := SM_BB_Chain{Entity := E}
        set M.Collidable = false
        Mat := MountMat(Brighten(P.Metal, 1.2), 0.35, 0.9, 0.0, color{}, 0.0, A)
        set Mat.ChainLength = ChainLen
        set Mat.ChainPitch = BB_ChainPitch
        set M.Chain = Mat
        E.AddComponents(array{M})
        Root.AddEntities(array{E})

    SpawnArch(Root:entity, P:boo_palette):void =
        E := NewChild(Root, 0.0, 0.0)
        M := SM_BB_Arch{Entity := E}
        set M.Collidable = false
        Still := StillMotion()
        set M.Wood = MountMat(P.Wood, 0.7, 0.0, 0.6, color{}, 0.0, Still)
        set M.Metal = MountMat(P.Metal, 0.38, 0.85, 0.0, color{}, 0.0, Still)
        set M.Pumpkins = PumpkinMat(P, true, Still)
        E.AddComponents(array{M})
        Root.AddEntities(array{E})
        Collider(Root, -225.0, 30.0, BB_BeamZ + 40.0)
        Collider(Root, 225.0, 30.0, BB_BeamZ + 40.0)

    SpawnLanternPost(Root:entity, P:boo_palette):void =
        E := NewChild(Root, 0.0, 0.0)
        M := SM_BB_LanternPost{Entity := E}
        set M.Collidable = false
        Still := StillMotion()
        set M.Wood = MountMat(P.Wood, 0.7, 0.0, 0.6, color{}, 0.0, Still)
        set M.Metal = MountMat(P.Metal, 0.38, 0.85, 0.0, color{}, 0.0, Still)
        set M.Glow = MountMat(Dim(P.Glow, 0.3), 0.3, 0.0, 0.0, P.Glow, 7.0, Still)
        set M.Pumpkins = PumpkinMat(P, true, Still)
        E.AddComponents(array{M})
        Root.AddEntities(array{E})
        Collider(Root, -250.0, 32.0, BB_BeamZ + 50.0)

    SpawnSpider(Root:entity, Up:float, P:boo_palette, A:boo_motion):void =
        E := NewChild(Root, 0.0, Up)
        M := SM_BB_SpiderThread{Entity := E}
        set M.Collidable = false
        set M.Silk = MountMat(color{R := 0.8, G := 0.8, B := 0.85}, 0.5, 0.0, 0.0, color{R := 0.8, G := 0.8, B := 1.0}, 0.6, A)
        set M.Spider = MountMat(color{R := 0.03, G := 0.015, B := 0.05}, 0.3, 0.0, 0.0, color{}, 0.0, A)
        set M.Eyes = MountMat(color{R := 1.0, G := 1.0, B := 1.0}, 0.3, 0.0, 0.0, P.Glow, 3.0, A)
        E.AddComponents(array{M})
        Root.AddEntities(array{E})

    SpawnFloatRing(Root:entity, P:boo_palette):void =
        E := NewChild(Root, 0.0, 0.0)
        M := SM_BB_FloatRing{Entity := E}
        set M.Collidable = false
        set M.Glow = MountMat(Dim(P.Glow, 0.3), 0.3, 0.0, 0.0, P.Glow, 5.0, StillMotion())
        E.AddComponents(array{M})
        Root.AddEntities(array{E})

    # An invisible box so players can't walk through a post.
    Collider(Root:entity, Left:float, Width:float, Height:float):void =
        E := NewChild(Root, Left, Height * 0.5)
        E.SetLocalTransform(transform{
            Translation := vector3{Forward := 0.0, Left := Left, Up := Height * 0.5},
            Rotation := IdentityRotation(),
            Scale := vector3{Forward := Width / 100.0, Left := Width / 100.0, Up := Height / 100.0}})
        Box := cube{Entity := E}
        set Box.Visible = false
        E.AddComponents(array{Box})
        Root.AddEntities(array{E})

    StillMotion():boo_motion = boo_motion{Speed := 1.0, Phase := 0.0, Sway := 0.0, PivotUp := 0.0, Bob := 0.0}

    # ---------------------------------------------------------------- materials (one instance per part)
    PanelMat(Top:color, Bottom:color, Rim:color, Emissive:color, Strength:float, DividerMode:float, RimOff:float, A:boo_motion):M_BB_Panel =
        M := M_BB_Panel{}
        set M.ColorTop = Top
        set M.ColorBottom = Bottom
        set M.RimColor = Rim
        set M.RimStrength = if (RimOff > 0.5) then 0.0 else 0.6
        set M.Emissive = Emissive
        set M.EmissiveStrength = Strength
        set M.Pulse = if (Strength > 0.0) then 0.18 else 0.0
        set M.DividerMode = DividerMode
        set M.Stretch = 1.0 - DividerMode
        set M.SplitZ = BB_SplitZ
        set M.DividerZ = BB_DividerZ
        set M.Speed = A.Speed
        set M.Phase = A.Phase
        set M.SwayDegrees = A.Sway
        set M.PivotUp = A.PivotUp
        set M.BobHeight = A.Bob
        set M.ClockMode = A.ClockMode
        set M.ClockAnchorX = A.AnchorX
        set M.ClockAnchorY = A.AnchorY
        set M.ClockAnchorZ = A.AnchorZ
        M

    CardMat(Mask:texture, Fill:color, Outline:color, Accent:color, AlwaysOn:float, CenterY:float, CenterZ:float, A:boo_motion):M_BB_Card =
        M := M_BB_Card{}
        set M.Mask = Mask
        set M.FillColor = Fill
        set M.OutlineColor = Outline
        set M.AccentColor = Accent
        set M.AlwaysOn = AlwaysOn
        set M.Shine = AlwaysOn
        set M.Glow = 0.32
        set M.InTime = BB_ThanksIn
        set M.OutTime = BB_ThanksOut
        set M.CenterY = CenterY
        set M.CenterZ = CenterZ
        set M.Speed = A.Speed
        set M.Phase = A.Phase
        set M.SwayDegrees = A.Sway
        set M.PivotUp = A.PivotUp
        set M.BobHeight = A.Bob
        set M.ClockMode = A.ClockMode
        set M.ClockAnchorX = A.AnchorX
        set M.ClockAnchorY = A.AnchorY
        set M.ClockAnchorZ = A.AnchorZ
        M

    ButtonMat(Mask:texture, InT:float, OutT:float, ClickT:float, CenterY:float, P:boo_palette, Active:color, A:boo_motion):M_BB_Button =
        M := M_BB_Button{}
        set M.Mask = Mask
        set M.InTime = InT
        set M.OutTime = OutT
        set M.ClickTime = ClickT
        set M.CenterY = CenterY
        set M.CenterZ = BB_ButtonZ
        set M.IdleColor = P.ButtonIdle
        set M.GlyphIdle = P.GlyphIdle
        set M.ActiveColor = Active
        set M.GlyphActive = color{R := 0.012, G := 0.012, B := 0.025}
        set M.OffTime = 99.0
        set M.ActiveGlow = 0.18
        set M.Speed = A.Speed
        set M.Phase = A.Phase
        set M.SwayDegrees = A.Sway
        set M.PivotUp = A.PivotUp
        set M.BobHeight = A.Bob
        set M.ClockMode = A.ClockMode
        set M.ClockAnchorX = A.AnchorX
        set M.ClockAnchorY = A.AnchorY
        set M.ClockAnchorZ = A.AnchorZ
        M

    BurstMat(Trigger:float, SetStart:float, ShowIt:logic, A:boo_motion):M_BB_Burst =
        M := M_BB_Burst{}
        set M.Atlas = T_BB_Sprites
        set M.TriggerTime = Trigger
        set M.SetStart = SetStart
        set M.SetCount = 3.0
        set M.Velocity = 120.0
        set M.Gravity = 45.0
        set M.Size = 34.0
        set M.Life = 0.95
        set M.Hide = if (ShowIt?) then 0.0 else 1.0
        set M.Phase = A.Phase
        set M.SwayDegrees = A.Sway
        set M.PivotUp = A.PivotUp
        set M.BobHeight = A.Bob
        set M.ClockMode = A.ClockMode
        set M.ClockAnchorX = A.AnchorX
        set M.ClockAnchorY = A.AnchorY
        set M.ClockAnchorZ = A.AnchorZ
        set M.Speed = A.Speed
        M

    CandyMat(A:boo_motion):M_BB_Burst =
        M := M_BB_Burst{}
        set M.Atlas = T_BB_Sprites
        set M.TriggerTime = BB_RainStart
        set M.Delay = 1.5
        set M.Life = 1.7
        set M.Velocity = 0.0
        set M.Gravity = 430.0
        set M.SpreadS = 175.0
        set M.Toward = 12.0
        set M.Size = 36.0
        set M.SetStart = 9.0
        set M.SetCount = 4.0
        set M.Spin = 1.4
        set M.Hide = if (ShowCandyRain?) then 0.0 else 1.0
        set M.Phase = A.Phase
        set M.SwayDegrees = A.Sway
        set M.PivotUp = A.PivotUp
        set M.BobHeight = A.Bob
        set M.ClockMode = A.ClockMode
        set M.ClockAnchorX = A.AnchorX
        set M.ClockAnchorY = A.AnchorY
        set M.ClockAnchorZ = A.AnchorZ
        set M.Speed = A.Speed
        M

    GhostMat(P:boo_palette, A:boo_motion):M_BB_Ghost =
        M := M_BB_Ghost{}
        set M.GlowColor = P.GhostGlow
        set M.Hide = if (ShowGhost?) then 0.0 else 1.0
        set M.Speed = A.Speed
        set M.Phase = A.Phase
        set M.SwayDegrees = A.Sway
        set M.PivotUp = A.PivotUp
        set M.BobHeight = A.Bob
        set M.ClockMode = A.ClockMode
        set M.ClockAnchorX = A.AnchorX
        set M.ClockAnchorY = A.AnchorY
        set M.ClockAnchorZ = A.AnchorZ
        M

    BatsMat(A:boo_motion):M_BB_Bats =
        M := M_BB_Bats{}
        set M.Atlas = T_BB_Sprites
        set M.Hide = if (ShowBats?) then 0.0 else 1.0
        set M.SwayDegrees = A.Sway
        set M.PivotUp = A.PivotUp
        set M.BobHeight = A.Bob
        set M.ClockMode = A.ClockMode
        set M.ClockAnchorX = A.AnchorX
        set M.ClockAnchorY = A.AnchorY
        set M.ClockAnchorZ = A.AnchorZ
        M

    PumpkinMat(P:boo_palette, ShowIt:logic, A:boo_motion):M_BB_Pumpkin =
        M := M_BB_Pumpkin{}
        set M.Face = T_BB_PumpkinFace
        set M.Color = P.Pumpkin
        set M.Hide = if (ShowIt?) then 0.0 else 1.0
        set M.SwayDegrees = A.Sway
        set M.PivotUp = A.PivotUp
        set M.BobHeight = A.Bob
        set M.ClockMode = A.ClockMode
        set M.ClockAnchorX = A.AnchorX
        set M.ClockAnchorY = A.AnchorY
        set M.ClockAnchorZ = A.AnchorZ
        M

    MountMat(Base:color, Rough:float, Metal:float, Grain:float, Emissive:color, Strength:float, A:boo_motion):M_BB_Mount =
        M := M_BB_Mount{}
        set M.Color = Base
        set M.Roughness = Rough
        set M.Metallic = Metal
        set M.Grain = Grain
        set M.Emissive = Emissive
        set M.EmissiveStrength = Strength
        set M.Flicker = if (Strength > 0.0) then 0.25 else 0.0
        set M.SwayDegrees = A.Sway
        set M.PivotUp = A.PivotUp
        set M.BobHeight = A.Bob
        set M.ClockMode = A.ClockMode
        set M.ClockAnchorX = A.AnchorX
        set M.ClockAnchorY = A.AnchorY
        set M.ClockAnchorZ = A.AnchorZ
        M

    # ---------------------------------------------------------------- texts
    HeadlineTexture():texture =
        case (Headline):
            boo_headline.HavingFun => T_BB_Header_1
            boo_headline.HappyHalloween => T_BB_Header_2
            boo_headline.SupportThisMap => T_BB_Header_3
            boo_headline.SpookyGoodTime => T_BB_Header_4
            _ => T_BB_Header_0

    ThanksTexture():texture =
        case (ThanksMessage):
            boo_thanks.ThankYou => T_BB_Thanks_1
            boo_thanks.YouRock => T_BB_Thanks_2
            boo_thanks.Spooktacular => T_BB_Thanks_3
            _ => T_BB_Thanks_0

    # ---------------------------------------------------------------- colours
    Palette():boo_palette =
        Base := StylePalette(Style)
        if (UseCustomColors?):
            boo_palette:
                BoardTop := BoardColor
                BoardBottom := Dim(BoardColor, 0.3)
                Rim := Brighten(BoardColor, 4.0)
                Trim := TrimColor
                Divider := TrimColor
                HeaderText := TextColor
                HeaderOutline := Dim(TrimColor, 0.35)
                HeaderAccent := SaveColor
                ThanksText := TextColor
                ThanksOutline := Dim(BoardColor, 2.0)
                ThanksAccent := FollowColor
                ButtonIdle := Brighten(BoardColor, 1.6)
                GlyphIdle := TextColor
                Like := LikeColor
                Save := SaveColor
                Follow := FollowColor
                GhostGlow := GhostGlowColor
                Wood := MountColor
                Metal := Brighten(MountColor, 2.0)
                Glow := TrimColor
                Pumpkin := Base.Pumpkin
        else:
            Base

    StylePalette(S:boo_style):boo_palette =
        case (S):
            boo_style.GhostlyMint => boo_palette:
                BoardTop := Col(0.02, 0.07, 0.08)
                BoardBottom := Col(0.005, 0.02, 0.03)
                Rim := Col(0.1, 0.6, 0.55)
                Trim := Col(0.15, 1.0, 0.7)
                Divider := Col(0.6, 0.9, 1.0)
                HeaderText := Col(0.9, 1.0, 0.97)
                HeaderOutline := Col(0.0, 0.18, 0.2)
                HeaderAccent := Col(0.6, 0.9, 1.0)
                ThanksText := Col(0.92, 1.0, 0.97)
                ThanksOutline := Col(0.0, 0.15, 0.2)
                ThanksAccent := Col(0.6, 1.0, 0.85)
                ButtonIdle := Col(0.019, 0.022, 0.042)
                GlyphIdle := Col(0.74, 0.75, 0.82)
                Like := Col(0.80, 0.76, 1.0)
                Save := Col(0.80, 0.76, 1.0)
                Follow := Col(0.80, 0.76, 1.0)
                GhostGlow := Col(0.3, 1.0, 0.8)
                Wood := Col(0.05, 0.06, 0.07)
                Metal := Col(0.12, 0.14, 0.15)
                Glow := Col(0.3, 1.0, 0.75)
                Pumpkin := Col(0.85, 0.9, 0.86)
            boo_style.WitchBrew => boo_palette:
                BoardTop := Col(0.03, 0.06, 0.02)
                BoardBottom := Col(0.008, 0.02, 0.006)
                Rim := Col(0.25, 0.6, 0.1)
                Trim := Col(0.25, 1.0, 0.05)
                Divider := Col(0.5, 0.1, 0.9)
                HeaderText := Col(0.85, 1.0, 0.6)
                HeaderOutline := Col(0.08, 0.2, 0.0)
                HeaderAccent := Col(0.6, 0.25, 1.0)
                ThanksText := Col(0.85, 1.0, 0.6)
                ThanksOutline := Col(0.15, 0.03, 0.25)
                ThanksAccent := Col(0.4, 1.0, 0.1)
                ButtonIdle := Col(0.019, 0.022, 0.042)
                GlyphIdle := Col(0.74, 0.75, 0.82)
                Like := Col(0.80, 0.76, 1.0)
                Save := Col(0.80, 0.76, 1.0)
                Follow := Col(0.80, 0.76, 1.0)
                GhostGlow := Col(0.5, 1.0, 0.3)
                Wood := Col(0.04, 0.03, 0.02)
                Metal := Col(0.08, 0.1, 0.07)
                Glow := Col(0.4, 1.0, 0.1)
                Pumpkin := Col(1.0, 0.33, 0.02)
            boo_style.BloodMoon => boo_palette:
                BoardTop := Col(0.09, 0.012, 0.015)
                BoardBottom := Col(0.025, 0.003, 0.005)
                Rim := Col(0.7, 0.05, 0.08)
                Trim := Col(1.0, 0.04, 0.03)
                Divider := Col(1.0, 0.45, 0.08)
                HeaderText := Col(1.0, 0.92, 0.85)
                HeaderOutline := Col(0.3, 0.0, 0.02)
                HeaderAccent := Col(1.0, 0.3, 0.2)
                ThanksText := Col(1.0, 0.92, 0.85)
                ThanksOutline := Col(0.25, 0.0, 0.02)
                ThanksAccent := Col(0.8, 0.02, 0.04)
                ButtonIdle := Col(0.019, 0.022, 0.042)
                GlyphIdle := Col(0.74, 0.75, 0.82)
                Like := Col(0.80, 0.76, 1.0)
                Save := Col(0.80, 0.76, 1.0)
                Follow := Col(0.80, 0.76, 1.0)
                GhostGlow := Col(1.0, 0.35, 0.3)
                Wood := Col(0.03, 0.02, 0.02)
                Metal := Col(0.08, 0.06, 0.06)
                Glow := Col(1.0, 0.15, 0.05)
                Pumpkin := Col(0.8, 0.15, 0.03)
            boo_style.CandyPop => boo_palette:
                BoardTop := Col(0.3, 0.05, 0.25)
                BoardBottom := Col(0.12, 0.02, 0.12)
                Rim := Col(1.0, 0.4, 0.8)
                Trim := Col(1.0, 0.3, 0.7)
                Divider := Col(0.3, 0.9, 1.0)
                HeaderText := Col(1.0, 1.0, 1.0)
                HeaderOutline := Col(0.5, 0.05, 0.3)
                HeaderAccent := Col(0.3, 0.9, 1.0)
                ThanksText := Col(1.0, 1.0, 1.0)
                ThanksOutline := Col(0.45, 0.05, 0.35)
                ThanksAccent := Col(0.3, 0.85, 1.0)
                ButtonIdle := Col(0.019, 0.022, 0.042)
                GlyphIdle := Col(0.74, 0.75, 0.82)
                Like := Col(0.80, 0.76, 1.0)
                Save := Col(0.80, 0.76, 1.0)
                Follow := Col(0.80, 0.76, 1.0)
                GhostGlow := Col(1.0, 0.6, 0.9)
                Wood := Col(0.2, 0.05, 0.15)
                Metal := Col(0.6, 0.5, 0.6)
                Glow := Col(1.0, 0.4, 0.8)
                Pumpkin := Col(1.0, 0.45, 0.1)
            _ => boo_palette:
                BoardTop := Col(0.075, 0.03, 0.12)
                BoardBottom := Col(0.02, 0.008, 0.035)
                Rim := Col(0.35, 0.12, 0.6)
                Trim := Col(0.95, 0.24, 0.01)
                Divider := Col(0.42, 0.06, 0.95)
                HeaderText := Col(1.0, 0.93, 0.8)
                HeaderOutline := Col(0.45, 0.1, 0.0)
                HeaderAccent := Col(0.55, 0.35, 1.0)
                ThanksText := Col(1.0, 0.93, 0.8)
                ThanksOutline := Col(0.22, 0.04, 0.38)
                ThanksAccent := Col(0.25, 0.9, 0.05)
                ButtonIdle := Col(0.019, 0.022, 0.042)
                GlyphIdle := Col(0.74, 0.75, 0.82)
                Like := Col(0.80, 0.76, 1.0)
                Save := Col(0.80, 0.76, 1.0)
                Follow := Col(0.80, 0.76, 1.0)
                GhostGlow := Col(0.45, 0.85, 1.0)
                Wood := Col(0.045, 0.028, 0.03)
                Metal := Col(0.09, 0.08, 0.1)
                Glow := Col(1.0, 0.45, 0.06)
                Pumpkin := Col(1.0, 0.33, 0.02)

    Col(R:float, G:float, B:float)<computes>:color = color{R := R, G := G, B := B}
    PillColor:color = color{R := 0.03, G := 0.034, B := 0.062}
    Dim(X:color, K:float)<computes>:color = color{R := X.R * K, G := X.G * K, B := X.B * K}
    Brighten(X:color, K:float)<computes>:color = color{R := Min(1.0, X.R * K), G := Min(1.0, X.G * K), B := Min(1.0, X.B * K)}

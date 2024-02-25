from bpy.props import EnumProperty

from enum import IntEnum


class State(IntEnum):
    NONE                           = 0
    Walking                        = 1
    Falling                        = 2
    Grabbing                       = 3
    WallRunningRight               = 4
    WallRunningLeft                = 5
    WallClimbing                   = 6
    SpringBoarding                 = 7
    SpeedVaulting                  = 8
    VaultOver                      = 9
    GrabPullUp                     = 10
    Jump                           = 11
    WallRunJump                    = 12
    GrabJump                       = 13
    IntoGrab                       = 14
    Crouch                         = 15
    Slide                          = 16
    Melee                          = 17
    Snatch                         = 18
    Barge                          = 19
    Landing                        = 20
    Climb                          = 21
    IntoClimb                      = 22
    WallKick                       = 23
    Turn180                        = 24
    TurnInAir180                   = 25
    LayOnGround                    = 26
    IntoZipLine                    = 27
    ZipLine                        = 28
    Balance                        = 29
    LedgeWalk                      = 30
    GrabTransfer                   = 31
    MeleeAir                       = 32
    DodgeJump                      = 33
    WallRunDodgeJump               = 34
    Stumble                        = 35
    Snatched                       = 36
    StepUp                         = 37
    RumpSlide                      = 38
    Interact                       = 39
    WallRun                        = 40
    BotStop                        = 41
    BotStartWalking                = 42
    BotStartRunning                = 43
    BotTurnRunning                 = 44
    BotTurnStanding                = 45
    ExitCover                      = 46
    Vertigo                        = 47
    MeleeSlide                     = 48
    WallClimbDodgeJump             = 49
    WallClimb180TurnJump           = 50
    WallClimbDodgeJumpLeft         = 51
    WallClimbDodgeJumpRight        = 52
    MeleeVault                     = 53
    BotMeleeSecondSwing            = 54
    StumbleHard                    = 55
    BotRoll                        = 56
    BotFlip                        = 57
    Backflip_OBSOLETE              = 58
    BackflipToRun_OBSOLETE         = 59
    Swing                          = 60
    Coil                           = 61
    MeleeWallrun                   = 62
    MeleeCrouch                    = 63
    BotJumpShort                   = 64
    BotJumpMedium                  = 65
    BotJumpLong                    = 66
    JumpIntoGrab                   = 67
    StandGrabHeaveBot              = 68
    BotMeleeDodge                  = 69
    FinishAttack                   = 70
    MeleeBarge                     = 71
    FallingUncontrolled            = 72
    SwingJump                      = 73
    AnimationPlayback              = 74
    EnterCover                     = 75
    Cover                          = 76
    StumbleFalling                 = 77
    SoftLanding                    = 78
    HeadButtedByCeleste            = 79
    MeleeOriginalCeleste_OBSOLETE  = 80
    AutoStepUp                     = 81
    MeleeAirAbove                  = 82
    MeleeCounterAttack_OBSOLETE    = 83
    Block                          = 84
    AirBarge                       = 85
    RB_Bullrush_OBSOLETE           = 86
    RB_Bullrush_End_OBSOLETE       = 87
    RB_HitWall_OBSOLETE            = 88
    RB_HitFence_OBSOLETE           = 89
    RB_Ledge_OBSOLETE              = 90
    SkillRoll                      = 91
    BotGetDistance                 = 92
    Cutscene                       = 93
    MAX                            = 94


# -----------------------------------------------------------------------------
def StateProperty(callback = None):
    def get_state_items(self, context):
        return [(str(data.value), data.name, '') for data in State]

    return EnumProperty(name='State', 
                        items=get_state_items, 
                        default=0, 
                        update=callback)
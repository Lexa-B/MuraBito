using UnrealBuildTool;

public class MuraBitoTarget : TargetRules
{
	public MuraBitoTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Game;
		DefaultBuildSettings = BuildSettingsVersion.V7;
		IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_8;
		ExtraModuleNames.Add("MuraBito");
	}
}

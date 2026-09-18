using UnrealBuildTool;

public class MuraBitoEditorTarget : TargetRules
{
	public MuraBitoEditorTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Editor;
		DefaultBuildSettings = BuildSettingsVersion.V7;
		IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_8;
		ExtraModuleNames.Add("MuraBito");
	}
}

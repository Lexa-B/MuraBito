#include "Materials.h"

#include "Materials/Material.h"
#include "Materials/MaterialInterface.h"
#include "MuraBitoLog.h"
#if WITH_EDITOR
#include "Materials/MaterialExpressionVertexColor.h"
#endif

namespace Materials
{
	UMaterialInterface* LitVertexColor()
	{
		UMaterialInterface* Material = LoadObject<UMaterialInterface>(nullptr, TEXT("/Engine/EngineDebugMaterials/VertexColorMaterial.VertexColorMaterial"));
		if (!Material)
		{
			UE_LOG(LogMuraBito, Warning, TEXT("VertexColorMaterial not found; using the default surface material"));
			Material = UMaterial::GetDefaultMaterial(MD_Surface);
		}
		return Material;
	}

	UMaterialInterface* MakeUnlitVertexColor(UObject* Outer)
	{
#if WITH_EDITOR
		UMaterial* Material = NewObject<UMaterial>(Outer, NAME_None, RF_Transient);
		if (UMaterialEditorOnlyData* EditorData = Material->GetEditorOnlyData())
		{
			UMaterialExpressionVertexColor* VertexColor = NewObject<UMaterialExpressionVertexColor>(Material);
			Material->GetExpressionCollection().AddExpression(VertexColor);
			EditorData->EmissiveColor.Connect(0, VertexColor);
			Material->SetShadingModel(MSM_Unlit);
			Material->PreEditChange(nullptr);
			Material->PostEditChange();
			return Material;
		}
		UE_LOG(LogMuraBito, Warning, TEXT("No editor-only material data; the overlay uses the lit vertex-color material"));
#endif
		return LitVertexColor();
	}
}

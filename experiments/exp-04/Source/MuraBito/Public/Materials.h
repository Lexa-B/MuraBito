#pragma once

#include "CoreMinimal.h"

class UMaterialInterface;
class UObject;

/** Materials without project assets: engine-provided ones, or ones built in code at runtime. */
namespace Materials
{
	/** Lit material whose base color is the mesh's vertex color (/Engine/EngineDebugMaterials/VertexColorMaterial). */
	MURABITO_API UMaterialInterface* LitVertexColor();

	/**
	 * Unlit material that shows the vertex color, built in code. Needs editor-only material data, so this works
	 * when running through UnrealEditor (editor, PIE and -game). Elsewhere it falls back to LitVertexColor().
	 * The caller must keep the result referenced (e.g. in a UPROPERTY) so it isn't garbage collected.
	 */
	MURABITO_API UMaterialInterface* MakeUnlitVertexColor(UObject* Outer);
}

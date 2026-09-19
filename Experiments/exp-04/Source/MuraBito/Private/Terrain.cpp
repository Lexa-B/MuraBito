#include "Terrain.h"

#include "Engine/CollisionProfile.h"
#include "Materials.h"
#include "MeshBuilders.h"
#include "MuraBitoLog.h"
#include "ProceduralMeshComponent.h"

ATerrain::ATerrain()
{
	PrimaryActorTick.bCanEverTick = false;
	Mesh = CreateDefaultSubobject<UProceduralMeshComponent>(TEXT("Mesh"));
	Mesh->bUseAsyncCooking = true;
	Mesh->SetCollisionProfileName(UCollisionProfile::BlockAll_ProfileName);
	RootComponent = Mesh;
}

void ATerrain::Build(const FTerrainHeight& Height, const FBox2D& Area, float Spacing)
{
	const FMeshData Data = MeshBuilders::BuildTerrain(Height, Area, Spacing);
	Mesh->CreateMeshSection_LinearColor(0, Data.Vertices, Data.Triangles, Data.Normals, Data.UVs, Data.Colors,
		TArray<FProcMeshTangent>(), /*bCreateCollision=*/ true);
	Mesh->SetMaterial(0, Materials::LitVertexColor());
	UE_LOG(LogMuraBito, Log, TEXT("Terrain: %d vertices, %d triangles"), Data.Vertices.Num(), Data.Triangles.Num() / 3);
}

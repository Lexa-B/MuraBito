#include "HexOverlay.h"

#include "Materials.h"
#include "MuraBitoLog.h"
#include "ProceduralMeshComponent.h"

AHexOverlay::AHexOverlay()
{
	PrimaryActorTick.bCanEverTick = false;
	Mesh = CreateDefaultSubobject<UProceduralMeshComponent>(TEXT("Mesh"));
	Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Mesh->SetCastShadow(false);
	RootComponent = Mesh;

	HoverParams.Width = 22.f;
	HoverParams.Lift = 14.f;
}

void AHexOverlay::Build(const FHexGrid& InGrid, const FTerrainHeight& InHeight)
{
	Grid = InGrid;
	Height = InHeight;
	Hover.Reset();

	if (!Material)
	{
		Material = Materials::MakeUnlitVertexColor(this);
	}

	const FMeshData Lines = MeshBuilders::BuildHexEdges(Grid, Height, LineParams, LineColor);
	Mesh->CreateMeshSection_LinearColor(LinesSection, Lines.Vertices, Lines.Triangles, Lines.Normals, Lines.UVs,
		Lines.Colors, TArray<FProcMeshTangent>(), /*bCreateCollision=*/ false);
	Mesh->SetMaterial(LinesSection, Material);
	Mesh->ClearMeshSection(HoverSection);
	UE_LOG(LogMuraBito, Log, TEXT("HexOverlay: %d tiles, %d line vertices"), Grid.NumTiles(), Lines.Vertices.Num());
}

void AHexOverlay::SetHover(TOptional<FHex> Hex)
{
	if (Hex == Hover)
	{
		return;
	}
	Hover = Hex;
	if (!Hover.IsSet())
	{
		Mesh->ClearMeshSection(HoverSection);
		return;
	}
	const FMeshData Outline = MeshBuilders::BuildHexOutline(Grid, Hover.GetValue(), Height, HoverParams, HoverColor);
	Mesh->CreateMeshSection_LinearColor(HoverSection, Outline.Vertices, Outline.Triangles, Outline.Normals, Outline.UVs,
		Outline.Colors, TArray<FProcMeshTangent>(), /*bCreateCollision=*/ false);
	Mesh->SetMaterial(HoverSection, Material);
}

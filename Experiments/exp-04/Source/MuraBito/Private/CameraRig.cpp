#include "CameraRig.h"

#include "Camera/CameraComponent.h"
#include "GameFramework/SpringArmComponent.h"

ACameraRig::ACameraRig()
{
	PrimaryActorTick.bCanEverTick = true;

	Pivot = CreateDefaultSubobject<USceneComponent>(TEXT("Pivot"));
	RootComponent = Pivot;

	Arm = CreateDefaultSubobject<USpringArmComponent>(TEXT("Arm"));
	Arm->SetupAttachment(Pivot);
	Arm->bDoCollisionTest = false;
	Arm->bEnableCameraLag = false;
	Arm->bUsePawnControlRotation = false;

	Camera = CreateDefaultSubobject<UCameraComponent>(TEXT("Camera"));
	Camera->SetupAttachment(Arm, USpringArmComponent::SocketName);

	ApplyZoom();
}

FZoomRange ACameraRig::ZoomRange() const
{
	FZoomRange Range;
	Range.NearArm = NearArm;
	Range.FarArm = FarArm;
	Range.NearPitch = NearPitch;
	Range.FarPitch = FarPitch;
	return Range;
}

void ACameraRig::ApplyZoom()
{
	const FZoomRange Range = ZoomRange();
	Arm->TargetArmLength = CameraMath::ArmLength(Range, Zoom01);
	Arm->SetRelativeRotation(FRotator(CameraMath::Pitch(Range, Zoom01), 0.f, 0.f));
}

void ACameraRig::Configure(const FBox2D& InBounds, float InBaseZ)
{
	Bounds = InBounds;
	BaseZ = InBaseZ;
	const FVector2D Clamped = CameraMath::ClampToBounds(FVector2D(GetActorLocation()), Bounds);
	SetActorLocation(FVector(Clamped.X, Clamped.Y, BaseZ));
}

void ACameraRig::AddPan(const FVector2D& ScreenDir) { PendingScreenPan += ScreenDir; }
void ACameraRig::AddPanWorld(const FVector2D& WorldDelta) { PendingWorldPan += WorldDelta; }

void ACameraRig::AddZoom(float Steps)
{
	TargetZoom01 = FMath::Clamp(TargetZoom01 + Steps * ZoomStep, 0.f, 1.f);
}

float ACameraRig::GetArmLength() const { return Arm->TargetArmLength; }

void ACameraRig::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	Zoom01 = FMath::FInterpTo(Zoom01, TargetZoom01, DeltaSeconds, ZoomSmoothing);
	ApplyZoom();

	const float Speed = CameraMath::PanSpeed(PanSpeed, ZoomRange(), Zoom01);
	const FVector2D Move = CameraMath::ScreenDirToWorld(PendingScreenPan.GetClampedToMaxSize(1.0)) * Speed * DeltaSeconds
		+ PendingWorldPan;
	PendingScreenPan = FVector2D::ZeroVector;
	PendingWorldPan = FVector2D::ZeroVector;

	const FVector2D Next = CameraMath::ClampToBounds(FVector2D(GetActorLocation()) + Move, Bounds);
	SetActorLocation(FVector(Next.X, Next.Y, BaseZ));
}
